"""長音訊 Whisper STT：自動分段處理，避免幻覺傳遞並支援平行執行。

用法:
  uv run python3 whisper_stt_long.py <AUDIO_PATH> <OUTPUT_DIR> [options]

位置參數:
  AUDIO_PATH: 音訊或影片檔案路徑
  OUTPUT_DIR: 輸出目錄（產出 .srt）

選項:
  --language LANG                    語言代碼（如 zh、en，預設自動偵測）
  --model MODEL                      mlx_whisper 模型（預設 mlx-community/whisper-large-v3-turbo）
  --segment-minutes N                每段長度（分鐘，預設 45）
  --hallucination-threshold FLOAT    --hallucination-silence-threshold（預設 2.0）
  --parallel N                       同時執行的 mlx_whisper 進程數（預設 1；M 系列建議 1-2）
  --force-segment                    即使音訊 <30 分鐘也強制分段
  --keep-segments                    保留 tmp_segments/ 暫存目錄（預設刪除）

流程：
  1. ffprobe 取得音訊總時長
  2. 若 >30 分鐘（或 --force-segment），用 ffmpeg 切段（-c copy 零重編碼）
  3. 對每段執行 mlx_whisper（可平行）
  4. 以「各段實際時長」計算累積 offset，合併所有段 SRT
  5. 若語言為中文（zh），自動用 OpenCC s2twp 繁體轉換產出 .zh-tw.clean.srt

產出：
  {basename}.srt              — 合併後的 SRT（原語言）
  {basename}.zh-tw.clean.srt  — 中文則額外產出繁體版
  tmp_segments/               — 暫存分段音訊 + 段 SRT（除非 --keep-segments 否則完成後刪除）

為什麼分段？
  1. **避免幻覺傳遞**：mlx_whisper 的 --condition-on-previous-text=True 會把前段的幻覺文字
     拉到後段繼續生成；分段後每段獨立 conditioning，單點幻覺不會擴散
  2. **可平行**：多段可同時跑（M 系列 ANE 允許有限度的並行）
  3. **timeout 控制**：每段獨立 subprocess call，單段失敗不拖整個流程
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


# ── 時間與 SRT 工具 ────────────────────────────────────────

def parse_srt_time(ts):
    """Parse SRT timestamp 'HH:MM:SS,mmm' to seconds (float)."""
    ts = ts.strip()
    h, m, rest = ts.split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def format_srt_time(seconds):
    """Format seconds to SRT timestamp 'HH:MM:SS,mmm'."""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def probe_duration(audio_path):
    """Return audio duration in seconds (float), or None if ffprobe fails."""
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', audio_path],
            capture_output=True, text=True, check=True, timeout=60,
        )
        return float(r.stdout.strip())
    except Exception as e:
        print(f"  ffprobe failed on {audio_path}: {e}")
        return None


# ── 分段與 Whisper ─────────────────────────────────────────

def segment_audio(audio_path, segments_dir, segment_seconds):
    """Use ffmpeg to split audio into fixed-duration segments. Returns list of segment paths."""
    os.makedirs(segments_dir, exist_ok=True)
    ext = os.path.splitext(audio_path)[1]
    pattern = os.path.join(segments_dir, f"seg_%03d{ext}")

    result = subprocess.run(
        ['ffmpeg', '-y', '-i', audio_path,
         '-c', 'copy',
         '-f', 'segment',
         '-segment_time', str(segment_seconds),
         '-reset_timestamps', '1',
         pattern],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ffmpeg failed: {result.stderr[-500:]}", file=sys.stderr)
        sys.exit(1)

    segs = sorted([f for f in os.listdir(segments_dir) if f.startswith('seg_')])
    return [os.path.join(segments_dir, f) for f in segs]


def run_mlx_whisper(seg_path, seg_output_dir, language, model, hall_threshold):
    """Run mlx_whisper on a single segment. Returns SRT path or None on failure."""
    cmd = [
        'mlx_whisper',
        '--model', model,
        '--output-format', 'srt',
        '--output-dir', seg_output_dir,
        '--hallucination-silence-threshold', str(hall_threshold),
        '--condition-on-previous-text', 'True',
        '--temperature', '0',
    ]
    if language:
        cmd.extend(['--language', language])
    cmd.append(seg_path)

    print(f"  [whisper] START {os.path.basename(seg_path)}")
    # No timeout here: each segment is bounded by --segment-minutes * ~5x realtime max
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [whisper] FAILED {os.path.basename(seg_path)}: {r.stderr[-300:]}")
        return None

    basename = os.path.splitext(os.path.basename(seg_path))[0]
    srt_path = os.path.join(seg_output_dir, f"{basename}.srt")
    if not os.path.exists(srt_path):
        print(f"  [whisper] no output srt for {basename}")
        return None

    # Count entries for progress reporting
    with open(srt_path, 'r', encoding='utf-8') as f:
        entry_count = f.read().count('-->')
    print(f"  [whisper] DONE {os.path.basename(seg_path)} ({entry_count} 條)")
    return srt_path


# ── 合併 ───────────────────────────────────────────────────

def merge_srts_with_precise_offsets(srt_paths, seg_paths, output_path):
    """Merge SRTs using each segment's actual probed duration as cumulative offset.
    Returns (total_entries, cum_offsets)."""
    # Calculate cumulative offsets from actual segment durations
    cum_offsets = [0.0]
    for seg in seg_paths:
        dur = probe_duration(seg) or 0.0
        cum_offsets.append(cum_offsets[-1] + dur)

    all_entries = []  # list of (start_sec, end_sec, text)
    for i, srt_path in enumerate(srt_paths):
        if srt_path is None or not os.path.exists(srt_path):
            print(f"  [merge] skipping missing segment {i}")
            continue
        offset = cum_offsets[i]

        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        blocks = re.split(r'\n\n+', content.strip())
        for block in blocks:
            lines = block.strip().split('\n')
            ts_line = None
            text_lines = []
            for line in lines:
                if '-->' in line and ts_line is None:
                    ts_line = line
                elif ts_line is not None:
                    text_lines.append(line)
            if ts_line is None or not text_lines:
                continue

            try:
                start_str, end_str = [x.strip() for x in ts_line.split('-->')]
                start_sec = parse_srt_time(start_str) + offset
                end_sec = parse_srt_time(end_str) + offset
            except Exception:
                continue

            text = '\n'.join(text_lines).strip()
            if text:
                all_entries.append((start_sec, end_sec, text))

    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, (start, end, text) in enumerate(all_entries, 1):
            f.write(f"{idx}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{text}\n\n")

    return len(all_entries), cum_offsets


# ── 主流程 ─────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument('audio_path')
    ap.add_argument('output_dir')
    ap.add_argument('--language', default=None, help='zh / en / None (auto-detect)')
    ap.add_argument('--model', default='mlx-community/whisper-large-v3-turbo')
    ap.add_argument('--segment-minutes', type=int, default=45,
                    help='Segment length in minutes (default 45)')
    ap.add_argument('--hallucination-threshold', type=float, default=2.0)
    ap.add_argument('--parallel', type=int, default=1,
                    help='Parallel mlx_whisper processes (default 1; M 系列建議 1-2)')
    ap.add_argument('--force-segment', action='store_true',
                    help='Force segmentation even if audio <30 minutes')
    ap.add_argument('--keep-segments', action='store_true',
                    help='Keep tmp_segments/ directory after completion')
    args = ap.parse_args()

    if not os.path.exists(args.audio_path):
        print(f"error: audio not found: {args.audio_path}", file=sys.stderr)
        return 1

    os.makedirs(args.output_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(args.audio_path))[0]

    # --- Step 1: probe duration ---
    print("=== Step 1: 偵測音訊時長 ===")
    duration = probe_duration(args.audio_path)
    if duration is None:
        print("  ffprobe 失敗，假設為長音訊並強制分段")
        duration = float('inf')
    else:
        print(f"  音訊時長: {duration:.0f}s ({duration / 60:.1f} 分鐘)")

    threshold_sec = 30 * 60
    use_segmentation = args.force_segment or (duration > threshold_sec)

    segments_dir = os.path.join(args.output_dir, 'tmp_segments')

    if not use_segmentation:
        # --- Single-shot mode ---
        print("\n=== Step 2: 單次 mlx_whisper（短音訊，無需分段） ===")
        srt_path = run_mlx_whisper(
            args.audio_path, args.output_dir, args.language, args.model,
            args.hallucination_threshold
        )
        if srt_path is None:
            return 1
        target = os.path.join(args.output_dir, f"{basename}.srt")
        if srt_path != target:
            shutil.move(srt_path, target)
        final_srt = target
    else:
        # --- Segmented mode ---
        print(f"\n=== Step 2: ffmpeg 分段（每段 {args.segment_minutes} 分鐘） ===")
        seg_seconds = args.segment_minutes * 60
        seg_files = segment_audio(args.audio_path, segments_dir, seg_seconds)
        print(f"  分段完成: {len(seg_files)} 段")
        for i, s in enumerate(seg_files):
            size_mb = os.path.getsize(s) / (1024 * 1024)
            dur = probe_duration(s)
            dur_str = f"{dur:.0f}s" if dur is not None else "?"
            print(f"    seg_{i:03d}: {size_mb:.1f} MB, {dur_str}")

        # --- Step 3: run mlx_whisper on each segment ---
        print(f"\n=== Step 3: mlx_whisper STT（平行度 {args.parallel}） ===")
        srt_paths = [None] * len(seg_files)

        def _run(idx_seg):
            idx, seg = idx_seg
            return idx, run_mlx_whisper(
                seg, segments_dir, args.language, args.model, args.hallucination_threshold
            )

        if args.parallel <= 1:
            for i, seg in enumerate(seg_files):
                _, p = _run((i, seg))
                srt_paths[i] = p
        else:
            with ThreadPoolExecutor(max_workers=args.parallel) as ex:
                for idx, p in ex.map(_run, enumerate(seg_files)):
                    srt_paths[idx] = p

        failed = sum(1 for p in srt_paths if p is None)
        if failed:
            print(f"  ⚠️ {failed}/{len(seg_files)} 段 STT 失敗")
        if failed == len(seg_files):
            print("  所有分段都失敗，無法合併")
            return 1

        # --- Step 4: merge with precise offsets ---
        print("\n=== Step 4: 合併 SRT（使用各段實際時長累積 offset） ===")
        final_srt = os.path.join(args.output_dir, f"{basename}.srt")
        total_entries, offsets = merge_srts_with_precise_offsets(
            srt_paths, seg_files, final_srt
        )
        print(f"  合併完成: {total_entries} 條字幕")
        print(f"  各段累積 offset: {['%.0fs' % o for o in offsets]}")
        print(f"  輸出: {final_srt}")

    # --- Step 5: OpenCC for Chinese ---
    if args.language == 'zh' and os.path.exists(final_srt):
        print("\n=== Step 5: OpenCC 簡轉繁 ===")
        try:
            import opencc
            converter = opencc.OpenCC('s2twp')
            with open(final_srt, 'r', encoding='utf-8') as f:
                content = f.read()
            converted = converter.convert(content)
            clean_path = os.path.join(args.output_dir, f"{basename}.zh-tw.clean.srt")
            with open(clean_path, 'w', encoding='utf-8') as f:
                f.write(converted)
            # Also overwrite the raw .srt with traditional
            with open(final_srt, 'w', encoding='utf-8') as f:
                f.write(converted)
            print(f"  繁體版: {clean_path}")
        except ImportError:
            print("  ⚠️ OpenCC 未安裝（uv pip install opencc-python-reimplemented）")

    # --- Cleanup tmp_segments ---
    if use_segmentation and not args.keep_segments and os.path.isdir(segments_dir):
        shutil.rmtree(segments_dir, ignore_errors=True)
        print(f"\n已清理 {segments_dir}")

    print("\n=== 完成 ===")
    print(f"SRT: {final_srt}")
    print("SUBS_AVAILABLE=YES")
    return 0


if __name__ == '__main__':
    sys.exit(main())

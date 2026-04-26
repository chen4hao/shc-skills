#!/usr/bin/env python3
"""將一或多個補丁 SRT（patch）疊加到基底 SRT（base）之上，取代指定時間區段。

典型使用場景：Whisper 在長音訊中段卡住產生幻覺（例如 16:47-22:47 的「對對對」重複條目），
先用 ffmpeg 切出該時段重跑 whisper_stt.py 得到新的 patch SRT，再用本腳本把 patch 合併回
base，自動取代 base 中對應時段的幻覺條目。

用法:
    uv run python3 patch_srt.py <base.srt> <out.srt> --patch PATH:OFFSET[:SKIP]
                                                     [--patch PATH:OFFSET[:SKIP] ...]

參數:
    base.srt        基底 SRT（含幻覺區段的原始檔）
    out.srt         輸出合併後的 SRT
    --patch         補丁規格，格式 PATH:OFFSET[:SKIP]
                      PATH   - 補丁 SRT 路徑（由 ffmpeg 切段後 whisper_stt.py 產出）
                      OFFSET - 時間偏移（秒），= ffmpeg -ss 切段起始秒數
                      SKIP   - （選填）跳過 patch 中結束時間早於 SKIP 秒的條目（patch-local 時間）
                               用來去除切段時前後 buffer 引入的重疊或 warm-up 段
                    可以重複 --patch 多次處理多個幻覺區段

行為:
    1. 每個 patch 依 SKIP 過濾後，所有條目時間戳加上 OFFSET
    2. patch 的覆蓋時間範圍（patch_start, patch_end）= [min+OFFSET, max+OFFSET]
    3. base 中「start 落在任何 patch 覆蓋範圍內」的條目被移除
    4. 合併所有保留的 base 條目 + 所有 patch 條目，按 start 時間排序，重新編號

範例:
    # 單一幻覺區段（16:47-22:47）補丁，切段從 16:30 開始（offset=990），buffer 17 秒（skip=17）
    uv run python3 patch_srt.py base.srt out.srt \\
        --patch /tmp/seg_middle.zh-tw.clean.srt:990:17

    # 兩個幻覺區段（16:47-22:47 和 26:46-33:31）的雙補丁
    uv run python3 patch_srt.py base.srt out.srt \\
        --patch /tmp/seg_middle.zh-tw.clean.srt:990:17 \\
        --patch /tmp/seg_tail.zh-tw.clean.srt:1590:16
"""
import argparse
import re
import sys
from pathlib import Path


def parse_timestamp(ts: str) -> float:
    """HH:MM:SS,mmm -> seconds."""
    m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", ts.strip())
    if not m:
        raise ValueError(f"Bad timestamp: {ts}")
    h, mn, s, ms = m.groups()
    return int(h) * 3600 + int(mn) * 60 + int(s) + int(ms) / 1000


def format_timestamp(sec: float) -> str:
    """seconds -> HH:MM:SS,mmm."""
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    mn = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{mn:02d}:{s:02d},{ms:03d}"


def parse_srt(content: str):
    """Parse SRT into list of (start_sec, end_sec, text_lines)."""
    blocks = re.split(r"\n\n+", content.strip())
    entries = []
    for block in blocks:
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        try:
            int(lines[0].strip())
        except ValueError:
            continue
        tm = re.match(r"(\S+)\s*-->\s*(\S+)", lines[1])
        if not tm:
            continue
        start = parse_timestamp(tm.group(1))
        end = parse_timestamp(tm.group(2))
        text_lines = lines[2:]
        entries.append((start, end, text_lines))
    return entries


def apply_offset_and_skip(entries, offset_sec: float, skip_before_sec: float):
    """Shift entries by offset_sec; drop entries with local end_sec <= skip_before_sec."""
    result = []
    for start, end, text in entries:
        if end <= skip_before_sec:
            continue
        result.append((start + offset_sec, end + offset_sec, text))
    return result


def parse_patch_spec(spec: str):
    """Parse 'PATH:OFFSET[:SKIP]' into (path, offset, skip).

    Uses rsplit to handle Windows-style paths or paths with colons (edge case);
    most paths are /tmp/... so plain split also works.
    """
    parts = spec.rsplit(":", 2)
    if len(parts) == 2:
        path, offset = parts
        skip = "0"
    elif len(parts) == 3:
        path, offset, skip = parts
    else:
        raise ValueError(f"Bad --patch spec (expect PATH:OFFSET[:SKIP]): {spec}")
    try:
        offset_sec = float(offset)
        skip_sec = float(skip)
    except ValueError:
        raise ValueError(f"OFFSET/SKIP must be numeric in: {spec}")
    return path, offset_sec, skip_sec


def write_srt(entries, path: Path):
    """Sort by start time, renumber, and write SRT."""
    entries = sorted(entries, key=lambda x: x[0])
    blocks = []
    for i, (start, end, text) in enumerate(entries, start=1):
        blocks.append(
            f"{i}\n{format_timestamp(start)} --> {format_timestamp(end)}\n"
            + "\n".join(text)
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return len(entries)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("base_srt", help="Base SRT (with hallucination regions)")
    ap.add_argument("out_srt", help="Output merged SRT")
    ap.add_argument(
        "--patch",
        action="append",
        required=True,
        metavar="PATH:OFFSET[:SKIP]",
        help="Patch spec (repeatable). OFFSET and SKIP in seconds.",
    )
    args = ap.parse_args()

    base_path = Path(args.base_srt)
    out_path = Path(args.out_srt)
    if not base_path.exists():
        print(f"error: base SRT not found: {base_path}", file=sys.stderr)
        return 1

    base_entries = parse_srt(base_path.read_text(encoding="utf-8"))
    print(f"base: {len(base_entries)} entries")

    # Parse all patches and compute covered ranges
    all_patch_entries = []
    covered_ranges = []  # list of (start_sec, end_sec)
    for spec in args.patch:
        path, offset_sec, skip_sec = parse_patch_spec(spec)
        patch_path = Path(path)
        if not patch_path.exists():
            print(f"error: patch SRT not found: {patch_path}", file=sys.stderr)
            return 1
        raw = parse_srt(patch_path.read_text(encoding="utf-8"))
        shifted = apply_offset_and_skip(raw, offset_sec, skip_sec)
        if not shifted:
            print(f"warning: patch {path} has no entries after SKIP={skip_sec}s",
                  file=sys.stderr)
            continue
        patch_start = min(s for s, _, _ in shifted)
        patch_end = max(e for _, e, _ in shifted)
        covered_ranges.append((patch_start, patch_end))
        all_patch_entries.extend(shifted)
        print(f"patch {patch_path.name}: {len(raw)} raw -> {len(shifted)} after "
              f"SKIP={skip_sec}s (offset={offset_sec}s); "
              f"covers {format_timestamp(patch_start)} - {format_timestamp(patch_end)}")

    # Remove base entries whose start falls in any covered range
    def in_any_range(t: float) -> bool:
        return any(lo <= t < hi for lo, hi in covered_ranges)

    base_kept = [(s, e, t) for (s, e, t) in base_entries if not in_any_range(s)]
    base_removed = len(base_entries) - len(base_kept)
    print(f"base: kept {len(base_kept)}, removed {base_removed} "
          f"(overlapped with patch ranges)")

    merged = base_kept + all_patch_entries
    n = write_srt(merged, out_path)
    print(f"merged total: {n} entries")
    print(f"written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

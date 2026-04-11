"""複製字幕和影音檔到最終位置。

用法（單一影片）:
  uv run python3 copy_files.py <TEMP_DIR> <DEST_DIR> <MEDIA_DIR> <PREFIX>

用法（多 P 影片，如 Bilibili anthology）:
  uv run python3 copy_files.py <TEMP_DIR> <DEST_DIR> <MEDIA_DIR> <PREFIX> --multi-part <BVID>

參數說明：
  TEMP_DIR: 暫存目錄（含 en.srt、zh-tw.srt、bilingual.srt 及影音檔）
  DEST_DIR: 筆記 + 字幕的儲存目錄
  MEDIA_DIR: 影音檔統一存放目錄
  PREFIX: 檔案名稱前綴（主檔名）
  --multi-part BVID: 多 P 影片模式，會自動偵測 {BVID}_p*.mp4 並批次複製為
                     {PREFIX}-p01.mp4 ~ -p{N}.mp4，同時若存在 .zh-tw.clean.srt
                     也會批次複製成 {PREFIX}-p01.zh-tw.srt ~ -p{N}.zh-tw.srt。
                     此模式下不會產出合併 SRT 檔（因為多 P 沒有虛構合併時間軸）。
"""
import argparse
import glob
import os
import re
import shutil
import sys


def single_mode(temp_dir, dest_dir, media_dir, prefix):
    """Single-video mode: copy en/zh-tw/bilingual SRT + 1 media file."""
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)

    # 複製英文字幕
    en_src = os.path.join(temp_dir, "en.srt")
    if os.path.exists(en_src):
        shutil.copy2(en_src, os.path.join(dest_dir, f"{prefix}.en.srt"))
    # 複製中文字幕
    zh_src = os.path.join(temp_dir, "zh-tw.srt")
    if os.path.exists(zh_src):
        shutil.copy2(zh_src, os.path.join(dest_dir, f"{prefix}.zh-tw.srt"))
    # 複製雙語字幕（檔名含 &，不可在 Bash 中直接 cp）
    bi_src = os.path.join(temp_dir, "bilingual.srt")
    if os.path.exists(bi_src):
        shutil.copy2(bi_src, os.path.join(dest_dir, f"{prefix}.en&cht.srt"))

    # 複製影音檔到統一影音目錄（僅在有下載影音檔時）
    media_copied = False
    for ext in ["mp4", "m4a", "webm"]:
        files = glob.glob(os.path.join(temp_dir, f"*.{ext}"))
        if files:
            shutil.copy2(files[0], os.path.join(media_dir, f"{prefix}.{ext}"))
            print(f"Copied media: {files[0]} -> {media_dir}/{prefix}.{ext}")
            media_copied = True
            break

    if not media_copied:
        print("No media file to copy (subtitles were available, skipped media download)")

    print(f"Subtitles copied to {dest_dir}")


def multi_part_mode(temp_dir, dest_dir, media_dir, prefix, bvid):
    """Multi-part mode: copy each {BVID}_pN.mp4 as {prefix}-pNN.mp4,
    and each {BVID}_pN.zh-tw.clean.srt as {prefix}-pNN.zh-tw.srt.
    No merged SRT produced (multi-P has no valid virtual merged timeline).
    """
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)

    # Clean up any wrongly-named single file from prior single-mode runs
    wrong = os.path.join(media_dir, f"{prefix}.mp4")
    if os.path.exists(wrong):
        os.remove(wrong)
        print(f"Removed wrong single file: {wrong}")

    pattern = os.path.join(temp_dir, f"{bvid}_p*.mp4")
    mp4_files = glob.glob(pattern)
    if not mp4_files:
        print(f"No parts found matching: {pattern}")
        sys.exit(1)

    # Sort by part number
    parts = []
    for f in mp4_files:
        m = re.search(rf"{re.escape(bvid)}_p(\d+)\.mp4$", f)
        if m:
            parts.append((int(m.group(1)), f))
    parts.sort()

    # Copy MP4 files
    for p_num, src in parts:
        dst = os.path.join(media_dir, f"{prefix}-p{p_num:02d}.mp4")
        shutil.copy2(src, dst)
        size_mb = os.path.getsize(dst) / (1024 * 1024)
        print(f"  p{p_num:02d} MP4 -> {dst} ({size_mb:.1f}MB)")

    # Copy SRT files (prefer .zh-tw.clean.srt, fall back to .srt)
    srt_copied = 0
    for p_num, mp4 in parts:
        candidates = [
            mp4.replace(".mp4", ".zh-tw.clean.srt"),
            mp4.replace(".mp4", ".srt"),
        ]
        src_srt = next((c for c in candidates if os.path.exists(c)), None)
        if src_srt is None:
            print(f"  p{p_num:02d} SRT: SKIP (no SRT found)")
            continue
        dst_srt = os.path.join(dest_dir, f"{prefix}-p{p_num:02d}.zh-tw.srt")
        shutil.copy2(src_srt, dst_srt)
        with open(dst_srt) as f:
            entries = f.read().count("-->")
        print(f"  p{p_num:02d} SRT -> {dst_srt} ({entries} entries)")
        srt_copied += 1

    print(f"Done. Copied {len(parts)} MP4 + {srt_copied}/{len(parts)} SRT files.")


def main():
    parser = argparse.ArgumentParser(
        description="Copy subtitles and media to final locations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("temp_dir")
    parser.add_argument("dest_dir")
    parser.add_argument("media_dir")
    parser.add_argument("prefix")
    parser.add_argument(
        "--multi-part",
        metavar="BVID",
        default=None,
        help="Multi-part mode: batch-copy {BVID}_p*.mp4 and .zh-tw.clean.srt files with -pNN suffix",
    )
    args = parser.parse_args()

    if args.multi_part:
        multi_part_mode(args.temp_dir, args.dest_dir, args.media_dir, args.prefix, args.multi_part)
    else:
        single_mode(args.temp_dir, args.dest_dir, args.media_dir, args.prefix)


if __name__ == "__main__":
    main()

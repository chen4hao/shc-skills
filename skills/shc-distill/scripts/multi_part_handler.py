"""Multi-part video handler for Bilibili anthology and similar multi-P sources.

Usage:
  # Run whisper STT on all {BVID}_p*.mp4 files sequentially
  uv run python3 multi_part_handler.py stt <TEMP_DIR> <BVID> [--language LANG] [--model MODEL]

  # Copy all MP4 parts to download dir, renaming to {prefix}-p01.mp4 ~ -p{N}.mp4
  uv run python3 multi_part_handler.py copy <TEMP_DIR> <DOWNLOAD_DIR> <prefix> <BVID>

  # Copy all .zh-tw.clean.srt files to project dir, renaming to {prefix}-p01.zh-tw.srt ~ -p{N}.zh-tw.srt
  uv run python3 multi_part_handler.py copy-srt <TEMP_DIR> <PROJECT_DIR> <prefix> <BVID>

  # List all parts and their durations
  uv run python3 multi_part_handler.py list <TEMP_DIR> <BVID>
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys


def discover_parts(temp_dir, bvid):
    """Return sorted list of (part_num, mp4_path) tuples."""
    pattern = os.path.join(temp_dir, f"{bvid}_p*.mp4")
    files = glob.glob(pattern)
    parts = []
    for f in files:
        m = re.search(rf"{re.escape(bvid)}_p(\d+)\.mp4$", f)
        if m:
            parts.append((int(m.group(1)), f))
    return sorted(parts)


def cmd_list(args):
    """List all parts with metadata."""
    parts = discover_parts(args.temp_dir, args.bvid)
    if not parts:
        print(f"No parts found: {args.temp_dir}/{args.bvid}_p*.mp4")
        sys.exit(1)
    print(f"Found {len(parts)} parts:")
    for i, (p_num, mp4) in enumerate(parts, 1):
        info_path = mp4.replace(".mp4", ".info.json")
        title = duration = "N/A"
        if os.path.exists(info_path):
            with open(info_path) as f:
                info = json.load(f)
            title = info.get("title", "N/A")
            duration = info.get("duration_string", "N/A")
        size_mb = os.path.getsize(mp4) / (1024 * 1024)
        print(f"  p{p_num:02d}: {title} | {duration} | {size_mb:.1f}MB")


def cmd_stt(args):
    """Run whisper_stt.py on all parts sequentially."""
    parts = discover_parts(args.temp_dir, args.bvid)
    if not parts:
        print(f"No parts found: {args.temp_dir}/{args.bvid}_p*.mp4")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    whisper_script = os.path.join(script_dir, "whisper_stt.py")

    print(f"Running Whisper STT on {len(parts)} parts...")
    failures = []
    for p_num, mp4 in parts:
        print(f"\n{'=' * 60}")
        print(f"== STT p{p_num:02d}: {mp4}")
        print(f"{'=' * 60}")
        cmd = ["uv", "run", "python3", whisper_script, mp4, args.temp_dir]
        if args.language:
            cmd.extend(["--language", args.language])
        if args.model:
            cmd.extend(["--model", args.model])
        result = subprocess.run(cmd, cwd=args.temp_dir)
        if result.returncode != 0:
            print(f"❌ p{p_num:02d} failed (exit code {result.returncode})")
            failures.append(p_num)
        else:
            print(f"✅ p{p_num:02d} complete")

    print(f"\n=== STT DONE ===")
    print(f"Success: {len(parts) - len(failures)}/{len(parts)}")
    if failures:
        print(f"Failed parts: {failures}")
        sys.exit(2)


def cmd_copy(args):
    """Copy all MP4 parts to dest dir, renaming with p-index."""
    parts = discover_parts(args.temp_dir, args.bvid)
    if not parts:
        print(f"No parts found: {args.temp_dir}/{args.bvid}_p*.mp4")
        sys.exit(1)

    # Clean up any wrongly-named single file left from copy_files.py
    wrong = os.path.join(args.dest_dir, f"{args.prefix}.mp4")
    if os.path.exists(wrong):
        os.remove(wrong)
        print(f"Removed wrong single file: {wrong}")

    os.makedirs(args.dest_dir, exist_ok=True)
    for p_num, src in parts:
        dst = os.path.join(args.dest_dir, f"{args.prefix}-p{p_num:02d}.mp4")
        shutil.copy2(src, dst)
        size_mb = os.path.getsize(dst) / (1024 * 1024)
        print(f"  p{p_num:02d} -> {dst} ({size_mb:.1f}MB)")
    print("Done.")


def cmd_copy_srt(args):
    """Copy all .zh-tw.clean.srt files to project dir, renaming with p-index.

    Outputs: {prefix}-p01.zh-tw.srt, {prefix}-p02.zh-tw.srt, ...
    """
    parts = discover_parts(args.temp_dir, args.bvid)
    if not parts:
        print(f"No parts found: {args.temp_dir}/{args.bvid}_p*.mp4")
        sys.exit(1)

    os.makedirs(args.dest_dir, exist_ok=True)
    copied = 0
    for p_num, mp4 in parts:
        src = mp4.replace(".mp4", ".zh-tw.clean.srt")
        if not os.path.exists(src):
            # Fall back to generic .srt
            alt = mp4.replace(".mp4", ".srt")
            if os.path.exists(alt):
                src = alt
            else:
                print(f"  p{p_num:02d}: SKIP (no SRT found)")
                continue
        dst = os.path.join(args.dest_dir, f"{args.prefix}-p{p_num:02d}.zh-tw.srt")
        shutil.copy2(src, dst)
        entries = 0
        with open(dst) as f:
            entries = f.read().count("-->")
        print(f"  p{p_num:02d} -> {dst} ({entries} entries)")
        copied += 1
    print(f"Done. Copied {copied}/{len(parts)} SRT files.")


def main():
    parser = argparse.ArgumentParser(description="Multi-part video handler")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List parts")
    p_list.add_argument("temp_dir")
    p_list.add_argument("bvid")
    p_list.set_defaults(func=cmd_list)

    p_stt = sub.add_parser("stt", help="Run Whisper STT on all parts")
    p_stt.add_argument("temp_dir")
    p_stt.add_argument("bvid")
    p_stt.add_argument("--language", default=None, help="Language code (zh, en, ...)")
    p_stt.add_argument("--model", default=None, help="Whisper model override")
    p_stt.set_defaults(func=cmd_stt)

    p_copy = sub.add_parser("copy", help="Copy all MP4 parts to dest dir")
    p_copy.add_argument("temp_dir")
    p_copy.add_argument("dest_dir")
    p_copy.add_argument("prefix")
    p_copy.add_argument("bvid")
    p_copy.set_defaults(func=cmd_copy)

    p_copy_srt = sub.add_parser("copy-srt", help="Copy all .zh-tw.clean.srt to project dir")
    p_copy_srt.add_argument("temp_dir")
    p_copy_srt.add_argument("dest_dir")
    p_copy_srt.add_argument("prefix")
    p_copy_srt.add_argument("bvid")
    p_copy_srt.set_defaults(func=cmd_copy_srt)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

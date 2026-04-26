#!/usr/bin/env python3
"""Finalize Chinese-only video distill: copy SRT + copy media + cleanup.

Usage:
  finalize_chinese_distill.py <tmp_dir> <project_dir> <video_id> <prefix> \
      [--download-dir DIR] [--skip-cleanup] [--fix-typos] \
      [--mishearing-pairs "k1=v1;k2=v2"]

One uv-run call replaces the 2 cp + 1 cleanup that previously closed out
a pure-Chinese YouTube/Bilibili/podcast distill (no EN translation pipeline).

Reads:
  {tmp_dir}/{video_id}.zh-tw.clean.srt   (produced by whisper_stt.py / whisper_stt_long.py)
  {tmp_dir}/{video_id}.{mp4|m4a|webm}    (first matching media file)

Writes:
  {project_dir}/{prefix}.zh-tw.srt       (traditional Chinese subtitles)
  {download_dir}/{prefix}.{ext}          (media file if present)

--fix-typos: load whisper_zh_typos.json and apply batch replacements to the
copied SRT. Opt-in because feedback_whisper_zh_common_typos.md default keeps
Whisper raw output; use when SRT/markdown consistency matters for reader.

--mishearing-pairs "k1=v1;k2=v2": episode-specific Whisper mishearing
corrections, parsed inline. Pairs separated by ; (or newline), key/value by =
or :. Each pair filtered through if old != new (skip same-word noise) and
applied to the copied SRT in order. Use this for one-off corrections (host
name, product name, episode-specific terms) that don't belong in the global
whisper_zh_typos.json. Per feedback_typo_replace_safety_check.md: each old
must be unique enough not to false-match other normal words (prefer 2-3 char
fragments over single chars).

Both --fix-typos and --mishearing-pairs can be used together; dict applies
first, then inline pairs.

Then runs cleanup.py (unless --skip-cleanup).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TYPO_DICT_PATH = SCRIPT_DIR / "whisper_zh_typos.json"


def apply_replacements(srt_path: str, pairs: list[tuple[str, str]], label: str) -> int:
    """Apply (old, new) replacements to srt_path in place. Skip same-word noise.
    Returns total number of replacements made."""
    if not pairs:
        return 0
    with open(srt_path) as f:
        content = f.read()
    total_replacements = 0
    hit_summary: list[tuple[str, str, int]] = []
    for old, new in pairs:
        if old == new:
            continue
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            total_replacements += count
            hit_summary.append((old, new, count))
    if total_replacements > 0:
        with open(srt_path, "w") as f:
            f.write(content)
        for old, new, count in hit_summary:
            print(f"  [{label}] {old} → {new} ({count}×)")
    return total_replacements


def apply_zh_typo_fixes(srt_path: str) -> int:
    """Apply batch replacements from whisper_zh_typos.json to srt_path in place."""
    if not TYPO_DICT_PATH.exists():
        print(f"⚠️ Typo dictionary not found: {TYPO_DICT_PATH} — skipping --fix-typos")
        return 0
    with open(TYPO_DICT_PATH) as f:
        data = json.load(f)
    pairs = [(e["wrong"], e["correct"]) for e in data.get("replacements", [])]
    return apply_replacements(srt_path, pairs, "typo-fix")


def parse_mishearing_pairs(spec: str) -> list[tuple[str, str]]:
    """Parse "k1=v1;k2=v2" or "k1:v1;k2:v2" or newline-separated forms.
    Mirrors finalize_video_distill.py --mishearing-pairs format."""
    pairs: list[tuple[str, str]] = []
    if not spec:
        return pairs
    raw_pairs = spec.replace("\n", ";").split(";")
    for raw in raw_pairs:
        raw = raw.strip()
        if not raw:
            continue
        if "=" in raw:
            old, _, new = raw.partition("=")
        elif ":" in raw:
            old, _, new = raw.partition(":")
        else:
            print(f"⚠️ Skipping malformed pair (no = or :): {raw!r}")
            continue
        old, new = old.strip(), new.strip()
        if old:
            pairs.append((old, new))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("tmp_dir", help="e.g. /tmp/distill-{VIDEO_ID}")
    ap.add_argument("project_dir", help="final notes directory")
    ap.add_argument("video_id")
    ap.add_argument("prefix", help="filename prefix, e.g. 2026-04-Author-Title")
    ap.add_argument(
        "--download-dir",
        default="/Users/chen4hao/Workspace/aiProjects/infoAggr/download",
    )
    ap.add_argument("--skip-cleanup", action="store_true")
    ap.add_argument(
        "--fix-typos",
        action="store_true",
        help="apply whisper_zh_typos.json batch replacements to the copied SRT",
    )
    ap.add_argument(
        "--mishearing-pairs",
        default="",
        help='inline episode-specific corrections, e.g. "肖玉依=蕭御醫;嘎命=Garmin" '
             "(see module docstring for format)",
    )
    args = ap.parse_args()

    os.makedirs(args.project_dir, exist_ok=True)
    os.makedirs(args.download_dir, exist_ok=True)

    # Step 1: copy Chinese SRT
    srt_src = os.path.join(args.tmp_dir, f"{args.video_id}.zh-tw.clean.srt")
    if not os.path.exists(srt_src):
        sys.exit(f"error: zh-tw SRT not found: {srt_src}")
    srt_dst = os.path.join(args.project_dir, f"{args.prefix}.zh-tw.srt")
    shutil.copy2(srt_src, srt_dst)
    with open(srt_dst) as f:
        entries = f.read().count("-->")
    print(f"✅ SRT copied: {srt_dst} ({entries} entries)")

    # Step 1.5a: optional global typo dict
    if args.fix_typos:
        print("=== Applying Whisper zh typo dictionary ===")
        fixed = apply_zh_typo_fixes(srt_dst)
        if fixed > 0:
            print(f"✅ Fixed {fixed} typo occurrences in SRT")
        else:
            print("ℹ️ No typos matched (SRT clean or dictionary has no overlap)")

    # Step 1.5b: optional inline mishearing pairs
    if args.mishearing_pairs:
        pairs = parse_mishearing_pairs(args.mishearing_pairs)
        if pairs:
            print(f"=== Applying {len(pairs)} inline mishearing pairs ===")
            fixed = apply_replacements(srt_dst, pairs, "mishearing")
            if fixed > 0:
                print(f"✅ Fixed {fixed} mishearing occurrences in SRT")
            else:
                print("ℹ️ No mishearing pairs matched")
        else:
            print("⚠️ --mishearing-pairs given but no valid pairs parsed")

    # Step 2: copy first media file if any. Prefer {video_id}.{ext}; fall back to
    # any matching extension in tmp_dir (covers cases where yt-dlp left a merged file).
    media_copied = False
    for ext in ("mp4", "m4a", "webm"):
        candidates = sorted(
            glob.glob(os.path.join(args.tmp_dir, f"{args.video_id}.{ext}"))
        )
        if not candidates:
            candidates = sorted(glob.glob(os.path.join(args.tmp_dir, f"*.{ext}")))
        if candidates:
            dst = os.path.join(args.download_dir, f"{args.prefix}.{ext}")
            shutil.copy2(candidates[0], dst)
            size_mb = os.path.getsize(dst) / (1024 * 1024)
            print(f"✅ Media copied: {dst} ({size_mb:.1f} MB)")
            media_copied = True
            break
    if not media_copied:
        print("ℹ️ No media file to copy (tmp_dir has no mp4/m4a/webm)")

    # Step 3: cleanup
    if args.skip_cleanup:
        print("⏸️ Skipping cleanup (--skip-cleanup)")
    else:
        result = subprocess.run(
            [
                "uv", "run", "python3", str(SCRIPT_DIR / "cleanup.py"),
                args.tmp_dir, args.project_dir, args.video_id,
            ]
        )
        if result.returncode != 0:
            sys.exit(f"cleanup.py failed (exit {result.returncode})")

    print("\n✅ Finalize complete (Chinese-only)", flush=True)


if __name__ == "__main__":
    main()

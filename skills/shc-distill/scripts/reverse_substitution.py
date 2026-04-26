#!/usr/bin/env python3
"""Reverse a wrong word/term substitution applied to distill output.

Use case: subagents were instructed to replace "OldTerm" with "NewTerm" globally
during translation, but the substitution turned out to be wrong (e.g., NewTerm
was a wrong guess at decoding the real product name from the auto-caption, when
in fact OldTerm was the real product name all along — visible in YouTube title).

This script restores OldTerm in all output files and renames them.

Usage:
  reverse_substitution.py <project_dir> <old_prefix> <new_prefix> <wrong_term> <correct_term>

Example (the 2026-04-21 OpenClaw episode):
  uv run python3 $SCRIPTS/reverse_substitution.py \\
    /Users/chen4hao/Workspace/aiProjects/infoAggr/Lenny-Rachitsky \\
    "2026-03-Claire-Vo-Claude-Code-Changed-My-Life" \\
    "2026-03-Claire-Vo-OpenClaw-Changed-My-Life" \\
    "Claude Code" \\
    "OpenClaw"

Operations (in order):
  1. In translated SRT files (.zh-tw.srt, .en&cht.srt): replace WRONG -> CORRECT
     (the .en.srt is original transcript, untouched by subagent translation)
  2. In markdown (.md): replace WRONG -> CORRECT, plus the hyphenated slug variant
     (e.g. "Claude-Code" -> "OpenClaw" for filename references in metadata)
  3. Rename all 4 files (.md, .en.srt, .zh-tw.srt, .en&cht.srt) from OLD_PREFIX to NEW_PREFIX
  4. Verification: count remaining occurrences of WRONG term (should be 0)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXTENSIONS = [".md", ".en.srt", ".zh-tw.srt", ".en&cht.srt"]
TRANSLATED_SRT_EXTS = [".zh-tw.srt", ".en&cht.srt"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir", help="Directory containing the distill output files")
    ap.add_argument("old_prefix", help="Current filename prefix (with the wrong term)")
    ap.add_argument("new_prefix", help="New filename prefix (with the correct term)")
    ap.add_argument("wrong_term", help="The wrongly-substituted term currently in files (e.g. 'Claude Code')")
    ap.add_argument("correct_term", help="The original/correct term to restore (e.g. 'OpenClaw')")
    args = ap.parse_args()

    proj = Path(args.project_dir)
    if not proj.is_dir():
        sys.exit(f"Project dir not found: {proj}")

    # 1. Replace in translated SRT files
    for ext in TRANSLATED_SRT_EXTS:
        src = proj / f"{args.old_prefix}{ext}"
        if not src.exists():
            print(f"SKIP (not found): {src.name}")
            continue
        content = src.read_text(encoding="utf-8")
        n = content.count(args.wrong_term)
        new_content = content.replace(args.wrong_term, args.correct_term)
        src.write_text(new_content, encoding="utf-8")
        print(f"SRT: {src.name}: replaced {n} occurrences of '{args.wrong_term}' -> '{args.correct_term}'")

    # 2. Replace in markdown (both spaced and hyphenated slug variants)
    md_src = proj / f"{args.old_prefix}.md"
    if md_src.exists():
        content = md_src.read_text(encoding="utf-8")
        n_spaced = content.count(args.wrong_term)
        wrong_slug = args.wrong_term.replace(" ", "-")
        correct_slug = args.correct_term.replace(" ", "-")
        n_slug = content.count(wrong_slug) if wrong_slug != args.wrong_term else 0
        new_content = content.replace(args.wrong_term, args.correct_term)
        if wrong_slug != args.wrong_term:
            new_content = new_content.replace(wrong_slug, correct_slug)
        md_src.write_text(new_content, encoding="utf-8")
        print(f"MD: {md_src.name}: replaced {n_spaced} '{args.wrong_term}' + {n_slug} '{wrong_slug}'")
    else:
        print(f"SKIP (not found): {md_src.name}")

    # 3. Rename all files
    for ext in EXTENSIONS:
        src = proj / f"{args.old_prefix}{ext}"
        dst = proj / f"{args.new_prefix}{ext}"
        if src.exists():
            src.rename(dst)
            print(f"Renamed: {src.name} -> {dst.name}")
        else:
            print(f"SKIP rename (not found): {src.name}")

    # 4. Verification
    print("\n=== Verification ===")
    all_clean = True
    for ext in [".md", ".zh-tw.srt", ".en&cht.srt"]:
        f = proj / f"{args.new_prefix}{ext}"
        if not f.exists():
            print(f"  {f.name}: missing")
            continue
        c = f.read_text(encoding="utf-8")
        wrong_count = c.count(args.wrong_term)
        correct_count = c.count(args.correct_term)
        status = "✓" if wrong_count == 0 else "✗"
        if wrong_count != 0:
            all_clean = False
        print(f"  {f.name}: '{args.wrong_term}'={wrong_count} (should be 0) {status}, '{args.correct_term}'={correct_count}")

    if all_clean:
        print("\n✅ Reverse substitution complete")
    else:
        print("\n⚠️  Some files still contain the wrong term — manual fix may be needed (e.g. metadata sections)")
        sys.exit(1)


if __name__ == "__main__":
    main()

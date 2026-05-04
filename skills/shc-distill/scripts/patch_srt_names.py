#!/usr/bin/env python3
"""Patch named-entity mishearings across multiple SRT/markdown files in one call.

Use this when finalize_video_distill.py has already run and you discover
additional mishearing pairs that need to be applied to the generated
.en.srt / .zh-tw.srt / .en&cht.srt files (and optionally a markdown note).

Why this exists instead of `sed -i`:
  Bash `sed -i` for in-place edits across multiple pre-existing files is
  systematically denied by the permission heuristic (see
  feedback_no_sed_inplace_multi_files). Calling this script is the
  pre-approved path.

Usage:
  uv run python3 patch_srt_names.py FILE [FILE ...] \\
      --pair "Bruce Mchuan=Bruce McEwen" \\
      --pair "Eric Kandell=Eric Kandel" \\
      --pair "Susumu Tonagawa=Susumu Tonegawa"

  # Or read pairs from a file (one `wrong=correct` per line, # for comments)
  uv run python3 patch_srt_names.py FILE [FILE ...] --pairs-file pairs.txt

Output (stdout):
  Per-file replacement counts; non-zero exit if a requested pair has zero
  matches across all files (so you don't accidentally ship a no-op).
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def parse_pair(s: str) -> tuple[str, str]:
    if "=" not in s:
        sys.exit(f"bad --pair (missing '='): {s!r}")
    wrong, correct = s.split("=", 1)
    if not wrong or not correct:
        sys.exit(f"bad --pair (empty side): {s!r}")
    return (wrong, correct)


def load_pairs_file(path: pathlib.Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pairs.append(parse_pair(line))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="Files to patch in-place.")
    ap.add_argument("--pair", action="append", default=[],
                    help="One mishearing pair 'wrong=correct'. Repeatable.")
    ap.add_argument("--pairs-file", type=pathlib.Path,
                    help="File with one 'wrong=correct' per line.")
    ap.add_argument("--allow-zero-matches", action="store_true",
                    help="Don't fail if a pair has zero matches.")
    args = ap.parse_args()

    pairs: list[tuple[str, str]] = [parse_pair(p) for p in args.pair]
    if args.pairs_file:
        pairs.extend(load_pairs_file(args.pairs_file))
    if not pairs:
        sys.exit("no pairs supplied (use --pair or --pairs-file)")

    pair_total: dict[tuple[str, str], int] = {p: 0 for p in pairs}

    for f in args.files:
        p = pathlib.Path(f)
        if not p.exists():
            sys.exit(f"file not found: {p}")
        text = p.read_text(encoding="utf-8")
        file_total = 0
        for wrong, correct in pairs:
            n = text.count(wrong)
            if n:
                text = text.replace(wrong, correct)
                pair_total[(wrong, correct)] += n
                print(f"  {p.name}: {wrong!r} -> {correct!r} x {n}")
                file_total += n
        if file_total:
            p.write_text(text, encoding="utf-8")
            print(f"  {p.name}: {file_total} replacements")
        else:
            print(f"  {p.name}: no matches")

    print("")
    print("=== Pair totals across all files ===")
    zero_pairs: list[tuple[str, str]] = []
    for (w, c), n in pair_total.items():
        marker = "✓" if n else "✗"
        print(f"  {marker} {w!r} -> {c!r}: {n} total")
        if n == 0:
            zero_pairs.append((w, c))

    if zero_pairs and not args.allow_zero_matches:
        print("", file=sys.stderr)
        print("ERROR: zero-match pairs detected (typo? wrong file?):",
              file=sys.stderr)
        for w, c in zero_pairs:
            print(f"  {w!r} -> {c!r}", file=sys.stderr)
        print("Re-run with --allow-zero-matches to suppress this check.",
              file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

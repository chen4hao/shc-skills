"""Batch-verify that candidate quotes appear verbatim in a source transcript.

Replaces N separate Grep calls with one script run. Useful before locking in
Key Quote section of a distill note.

Input:
  --source <path>    — the source file (e.g. all_transcripts.md)
  --quotes <path>    — quotes file, one quote per line (blank lines ignored)
                       OR pass quotes positionally after --

Output to stdout:
  PASS: <quote>      — quote found verbatim
  FAIL: <quote>      — quote NOT found (needs paraphrase check or drop)
Exit code: 0 if all pass, 1 if any fail.

Usage:
  uv run python3 $SCRIPTS/verify_quotes.py \\
    --source /tmp/.../all_transcripts.md \\
    --quotes /tmp/.../candidate_quotes.txt

  # Inline quotes (newline-separated) via stdin:
  echo "the agent is the muscle\\nrun slow to run fast" | \\
    uv run python3 $SCRIPTS/verify_quotes.py --source ... --stdin
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="Source text file to search in")
    ap.add_argument("--quotes", help="Quotes file (one per line)")
    ap.add_argument("--stdin", action="store_true", help="Read quotes from stdin (one per line)")
    ap.add_argument("--case-insensitive", action="store_true", help="Case-insensitive match")
    ap.add_argument("--normalize-space", action="store_true", default=True,
                    help="Collapse all whitespace runs in both source and quote before matching (default: true)")
    args = ap.parse_args()

    src_path = pathlib.Path(args.source)
    if not src_path.exists():
        print(f"ERROR: source file not found: {src_path}", file=sys.stderr)
        return 2

    if args.quotes:
        raw = pathlib.Path(args.quotes).read_text(encoding="utf-8")
    elif args.stdin:
        raw = sys.stdin.read()
    else:
        print("ERROR: provide --quotes FILE or --stdin", file=sys.stderr)
        return 2

    quotes = [q.strip() for q in raw.splitlines() if q.strip()]
    if not quotes:
        print("ERROR: no quotes to check", file=sys.stderr)
        return 2

    source = src_path.read_text(encoding="utf-8")

    if args.normalize_space:
        import re
        source_n = re.sub(r"\s+", " ", source)
    else:
        source_n = source
    if args.case_insensitive:
        source_cmp = source_n.lower()
    else:
        source_cmp = source_n

    fails = 0
    for q in quotes:
        q_n = q
        if args.normalize_space:
            import re
            q_n = re.sub(r"\s+", " ", q_n).strip()
        q_cmp = q_n.lower() if args.case_insensitive else q_n
        if q_cmp in source_cmp:
            print(f"PASS: {q[:120]}")
        else:
            print(f"FAIL: {q[:120]}")
            fails += 1

    print(f"\n=== {len(quotes) - fails}/{len(quotes)} passed ===")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Suggest Read-tool offset/limit batches for a text file.

Chinese text is ~3-5x denser in tokens than English, so Read must use smaller
limits (default 35 lines) to stay under the 10k-token cap. This script scans
the file, auto-detects language, and prints a list of safe Read batches.

Usage:
  uv run python3 read_plan.py <file> [--start LINE] [--end LINE]

Output (one batch per line):
  offset=N  limit=M   # approx KB

Example:
  read_plan.py ch000.txt --start 59 --end 158
"""
import sys, os, argparse

def is_chinese(sample: bytes) -> bool:
    try:
        s = sample.decode("utf-8", errors="ignore")
    except Exception:
        return False
    han = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
    return han > len(s) * 0.15

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=None)
    args = ap.parse_args()

    if not os.path.isfile(args.path):
        print(f"ERROR: not a file: {args.path}", file=sys.stderr)
        sys.exit(1)

    with open(args.path, "rb") as f:
        head = f.read(4096)
    zh = is_chinese(head)

    with open(args.path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    total = len(lines)
    end = args.end if args.end else total
    start = max(1, args.start)
    end = min(total, end)

    # Chinese: 35 lines per batch; English: 150 lines per batch.
    # Further shrink if avg line is very long.
    segment = lines[start-1:end]
    avg_bytes = (sum(len(l.encode("utf-8")) for l in segment) / max(1, len(segment)))
    base = 35 if zh else 150
    # Heuristic: keep each batch <= ~6 KB to stay well under 10k token cap
    max_bytes = 6000
    limit = min(base, max(10, int(max_bytes / max(1, avg_bytes))))

    lang = "ZH (中文)" if zh else "EN/other"
    print(f"# file: {args.path}")
    print(f"# total lines: {total}  range: {start}-{end}  lang: {lang}")
    print(f"# avg line: {avg_bytes:.0f} bytes  → batch limit: {limit} lines")
    print()

    cur = start
    while cur <= end:
        batch_end = min(cur + limit - 1, end)
        kb = sum(len(l.encode("utf-8")) for l in lines[cur-1:batch_end]) / 1024
        print(f"offset={cur}  limit={batch_end - cur + 1}   # ~{kb:.1f} KB")
        cur = batch_end + 1

if __name__ == "__main__":
    main()

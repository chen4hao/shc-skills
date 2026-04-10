#!/usr/bin/env python3
"""Remove epub_extract.py-generated ch*__*.txt files from a project dir.

Usage: uv run python3 cleanup_epub_txt.py <project_dir>
"""
import sys, glob, os

if len(sys.argv) != 2:
    print("Usage: cleanup_epub_txt.py <project_dir>", file=sys.stderr)
    sys.exit(1)

d = sys.argv[1]
removed = 0
for pat in ("ch*__*.txt", "ch[0-9][0-9][0-9]_*.txt"):
    for f in glob.glob(os.path.join(d, pat)):
        os.remove(f)
        removed += 1
print(f"Removed {removed} txt files from {d}")

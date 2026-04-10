#!/usr/bin/env python3
"""Remove epub_extract.py-generated temp files from a project dir.

Cleans up:
  - ch*__*.txt and ch###_*.txt files in the project dir
  - _distill_template.md
  - _tmp_extract/ subdirectory (used by epub extraction for subagent access)

Usage: uv run python3 cleanup_epub_txt.py <project_dir>
"""
import sys, glob, os, shutil

if len(sys.argv) != 2:
    print("Usage: cleanup_epub_txt.py <project_dir>", file=sys.stderr)
    sys.exit(1)

d = sys.argv[1]
removed = 0
for pat in ("ch*__*.txt", "ch[0-9][0-9][0-9]_*.txt", "_distill_template.md"):
    for f in glob.glob(os.path.join(d, pat)):
        os.remove(f)
        removed += 1

# Clean up _tmp_extract/ subdirectory if it exists
tmp_extract = os.path.join(d, "_tmp_extract")
if os.path.isdir(tmp_extract):
    count = len(os.listdir(tmp_extract))
    shutil.rmtree(tmp_extract)
    removed += count
    print(f"Removed _tmp_extract/ ({count} files)")

print(f"Removed {removed} files total from {d}")

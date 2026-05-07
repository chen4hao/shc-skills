#!/usr/bin/env python3
"""Remove epub_extract.py-generated temp files from a project dir.

Cleans up:
  - ch*__*.txt and ch###_*.txt files in the project dir
  - _distill_template.md
  - _tmp_extract/ and _tmp_extract_<hash>/ subdirectories (both legacy and --isolate forms)

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

# Clean up _tmp_extract/ and _tmp_extract_<hash>/ subdirectories.
# Glob matches both legacy name (no suffix) and --isolate name (with hash suffix).
tmp_extract_matches = glob.glob(os.path.join(d, "_tmp_extract*"))
if tmp_extract_matches:
    for tmp_extract in tmp_extract_matches:
        if os.path.isdir(tmp_extract):
            count = len(os.listdir(tmp_extract))
            shutil.rmtree(tmp_extract)
            removed += count
            print(f"Removed {os.path.basename(tmp_extract)}/ ({count} files)")
        else:
            print(
                f"NOTE: {os.path.basename(tmp_extract)} matched glob but is not a directory; skipped",
                file=sys.stderr,
            )
else:
    print(f"NOTE: no _tmp_extract*/ subdirs found in {d}", file=sys.stderr)

# Post-cleanup residue check: catches script bugs / racing writes.
# If any _tmp_extract*/ survives the cleanup loop, warn loudly to stderr so the
# caller cannot silently miss leftover dirs (this would have caught the
# 2026-05-07 The Quants run where cleanup reported 0 but state was unclear).
post_check = [p for p in glob.glob(os.path.join(d, "_tmp_extract*")) if os.path.isdir(p)]
if post_check:
    print(
        f"WARN: _tmp_extract*/ still present after cleanup: "
        f"{[os.path.basename(p) for p in post_check]}",
        file=sys.stderr,
    )

print(f"Removed {removed} files total from {d}")

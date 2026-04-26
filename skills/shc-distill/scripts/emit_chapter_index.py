#!/usr/bin/env python3
"""Emit markdown chapter index table from book distill author directory.

After assemble_book_notes.py writes chapter .md files with varying slug
conventions (50-char truncation, inconsistent trailing hyphens), the
彙總 summary needs a correct chapter index table. This script scans the
author directory and emits the table ready to paste into the 彙總.

Usage:
    uv run python3 emit_chapter_index.py <author_dir> [--prefix <prefix>]

Output (stdout):
    | 章節 | 主題 | 檔案 |
    |------|------|------|
    | Ch0 | Introduction | [Ch0](./{prefix}-Ch0-Introduction.md) |
    | Ch1 | 目前精神醫療走不通 | [Ch1](./{prefix}-Ch1-...) |
    ...

Title detection priority:
    1. H2 line Chinese portion after em-dash: "## Brain Energy — 目前精神醫療走不通"
    2. H1 English title: "# Ch1: What We're Doing Isn't Working"
    3. Fallback: slug with dashes converted to spaces
"""

import argparse
import re
import sys
from pathlib import Path

CH_FILE_RE = re.compile(r"^(.+)-Ch(\d+)-(.+)\.md$")
H1_CH_RE = re.compile(r"^#\s+Ch(\d+):\s*(.+?)\s*$", re.MULTILINE)


def extract_title(md_path: Path) -> str:
    """Extract chapter title from first ~2KB of markdown file."""
    try:
        with md_path.open("r", encoding="utf-8") as f:
            head = f.read(2000)
    except OSError:
        return ""

    # Priority 1: H2 line with Chinese after em-dash
    for line in head.splitlines()[:25]:
        stripped = line.strip()
        if stripped.startswith("## ") and "—" in stripped:
            content = stripped[3:].strip()
            chinese = content.split("—", 1)[1].strip()
            if chinese:
                return chinese

    # Priority 2: H1 English title (Ch{N}: {Title} format)
    m = H1_CH_RE.search(head)
    if m:
        return m.group(2).strip()

    return ""


def slug_to_title(slug: str) -> str:
    """Fallback: convert slug like 'What-Were-Doing' to 'What Were Doing'."""
    return slug.rstrip("-").replace("-", " ")


def main():
    ap = argparse.ArgumentParser(
        description="Emit markdown chapter index table for book distill 彙總"
    )
    ap.add_argument(
        "author_dir", help="Directory containing {prefix}-Ch{N}-*.md files"
    )
    ap.add_argument(
        "--prefix",
        default=None,
        help="File prefix filter (default: auto-detect if uniform across files)",
    )
    args = ap.parse_args()

    author_path = Path(args.author_dir)
    if not author_path.is_dir():
        print(f"ERROR: {author_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    chapters = []
    for md_file in sorted(author_path.iterdir()):
        if not md_file.is_file():
            continue
        m = CH_FILE_RE.match(md_file.name)
        if not m:
            continue
        prefix, ch_num_str, slug = m.groups()
        if args.prefix and prefix != args.prefix:
            continue
        chapters.append((int(ch_num_str), slug, md_file.name, prefix, md_file))

    if not chapters:
        print("ERROR: no chapter files matched", file=sys.stderr)
        sys.exit(1)

    if not args.prefix:
        prefixes = {c[3] for c in chapters}
        if len(prefixes) > 1:
            print(
                f"ERROR: multiple prefixes found: {sorted(prefixes)}; use --prefix",
                file=sys.stderr,
            )
            sys.exit(1)

    chapters.sort(key=lambda x: x[0])

    print("| 章節 | 主題 | 檔案 |")
    print("|------|------|------|")
    for ch_num, slug, filename, _, md_path in chapters:
        title = extract_title(md_path) or slug_to_title(slug)
        print(f"| Ch{ch_num} | {title} | [Ch{ch_num}](./{filename}) |")


if __name__ == "__main__":
    main()

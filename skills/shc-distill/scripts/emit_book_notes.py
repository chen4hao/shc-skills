#!/usr/bin/env python3
"""Emit book chapter/group notes from subagent task output JSONL files.

Replaces manual Write × N for book distill when skipping assemble_book_notes.py
(small book case: ≤12 subagents, each produces one complete chapter/group note).

Reads each task's .output JSONL, extracts the final assistant message (full
chapter/group note), cleans HTML entities and code fences, writes each as
    {prefix}-Ch{N}-{title-slug}.md   (chapter-mode H1: `# Ch{N}: ...`)
    {prefix}-Group{N}-{title-slug}.md (group-mode H1: `# Group{N}: ...`)
under the project output directory.

Usage:
    uv run python3 $SCRIPTS/emit_book_notes.py \\
      <tasks_dir> <output_dir> <prefix> [--dry-run]

Arguments:
    tasks_dir      — parent dir of .output JSONL files (from task notifications)
    output_dir     — where to write notes (e.g. /Users/.../陳俊旭/)
    prefix         — filename prefix e.g. "2026-04-更新粒線體根治慢性病"

Filename format (auto-detected from H1 prefix):
    {prefix}-Ch{N}-{title-slug}.md       — when H1 is `# Ch{N}: {title}`
    {prefix}-Group{N}-{title-slug}.md    — when H1 is `# Group{N}: {title}`

Title extraction (priority order):
    1. H1 `# Ch{N}: {title}` or `# Group{N}: {title}` — from the note itself
    2. Skip with warning if no matching H1

HTML entity cleaning:
    &gt; → >    &lt; → <    &amp; → &
    (subagents return these even when prompt forbids; known sonnet behavior)

Code fence stripping:
    Leading/trailing ```markdown / ``` wrappers if present.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Matches `# Ch{N}: {title}` or `# Group{N}: {title}` (full/half-width colon)
H1_RE = re.compile(r"^#\s*(Ch|Group)(\d+)\s*[:：]\s*(.+?)\s*$", re.MULTILINE)
CODE_FENCE_START = re.compile(r"^```(?:markdown|md)?\s*\n", re.MULTILINE)
CODE_FENCE_END = re.compile(r"\n```\s*$", re.MULTILINE)


def clean_html_entities(text: str) -> str:
    """Remove HTML entities that sonnet subagents insert despite prompt."""
    return (
        text.replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )


def strip_code_fences(text: str) -> str:
    """Strip leading ```markdown ... ``` wrapper if present."""
    text = CODE_FENCE_START.sub("", text, count=1)
    text = CODE_FENCE_END.sub("", text, count=1)
    return text.strip()


def strip_preamble_postamble(text: str) -> str:
    """Remove preamble before first H1 and postamble after last </details>.

    Subagents often prepend '現在我已讀取完整的章節內容。讓我根據模板格式撰寫萃取筆記。'
    and append '萃取完成，請主代理寫入...' despite prompt instructions.
    """
    # find first line starting with # Ch{N} or # Group{N}
    lines = text.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if H1_RE.match(line):
            start_idx = i
            break

    # find last line containing </details>
    end_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if "</details>" in lines[i]:
            end_idx = i + 1
            break

    if start_idx == 0 and end_idx == len(lines):
        # neither marker found; return cleaned input
        return text.strip()

    return "\n".join(lines[start_idx:end_idx]).strip()


def extract_final_assistant_text(output_file: Path) -> str | None:
    """Parse JSONL, return the final assistant message's text content.

    Task .output files have nested structure: msg.message.role / msg.message.content
    where content is either a string or a list of content blocks.
    """
    last_assistant_text: str | None = None
    try:
        with output_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Nested structure: msg.message.role
                message = msg.get("message") or {}
                role = message.get("role")
                if role != "assistant":
                    continue

                content = message.get("content")
                # content may be str or list of blocks
                if isinstance(content, str):
                    last_assistant_text = content
                elif isinstance(content, list):
                    # collect all text blocks
                    texts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                texts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            texts.append(block)
                    if texts:
                        last_assistant_text = "\n".join(texts)
    except FileNotFoundError:
        print(f"WARN: not found: {output_file}", file=sys.stderr)
        return None

    return last_assistant_text


def parse_h1(content: str) -> tuple[str, int, str] | None:
    """Parse H1 '# Ch{N}: {title}' or '# Group{N}: {title}'.

    Returns (h_prefix, N, title) where h_prefix is "Ch" or "Group", or None.
    """
    for m in H1_RE.finditer(content):
        try:
            h_prefix = m.group(1)  # "Ch" or "Group"
            n = int(m.group(2))
            title = m.group(3).strip()
            return (h_prefix, n, title)
        except ValueError:
            continue
    return None


def slugify_chinese(title: str) -> str:
    """Make a filesystem-safe title (keep Chinese, drop punctuation)."""
    # keep alnum, CJK, and hyphen; drop everything else
    s = re.sub(r"[^\w一-鿿㐀-䶿-]", "", title)
    return s[:60]  # cap length


def emit(
    tasks_dir: Path,
    output_dir: Path,
    prefix: str,
    dry_run: bool = False,
) -> int:
    """Process all .output files in tasks_dir, write .md files to output_dir.

    Returns number of notes written.
    """
    output_files = sorted(tasks_dir.glob("*.output"))
    if not output_files:
        print(f"ERROR: no .output files in {tasks_dir}", file=sys.stderr)
        return 0

    written = 0
    errors = 0
    for out_file in output_files:
        raw = extract_final_assistant_text(out_file)
        if raw is None:
            print(f"[skip] {out_file.name}: no assistant message", file=sys.stderr)
            errors += 1
            continue

        # clean in order: fences → entities → preamble/postamble
        cleaned = strip_code_fences(raw)
        cleaned = clean_html_entities(cleaned)
        cleaned = strip_preamble_postamble(cleaned)

        h1 = parse_h1(cleaned)
        if h1 is None:
            print(
                f"[skip] {out_file.name}: no '# Ch{{N}}: ...' or '# Group{{N}}: ...' H1 found",
                file=sys.stderr,
            )
            errors += 1
            continue

        h_prefix, n, title = h1
        slug = slugify_chinese(title)
        filename = f"{prefix}-{h_prefix}{n}-{slug}.md"
        dest = output_dir / filename

        if dry_run:
            print(f"[dry] {h_prefix}{n}: {title}  →  {filename}  ({len(cleaned)} chars)")
            continue

        dest.write_text(cleaned + "\n", encoding="utf-8")
        print(f"[ok]  {h_prefix}{n}: {title}  →  {filename}", file=sys.stderr)
        written += 1

    print(f"\nDone: wrote {written} files, {errors} errors", file=sys.stderr)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks_dir", type=Path, help="Directory containing .output JSONL files")
    ap.add_argument("output_dir", type=Path, help="Project output directory for .md files")
    ap.add_argument("prefix", help="Filename prefix, e.g. '2026-04-更新粒線體根治慢性病'")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be written")
    args = ap.parse_args()

    tasks_dir = args.tasks_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not tasks_dir.is_dir():
        print(f"ERROR: tasks_dir is not a directory: {tasks_dir}", file=sys.stderr)
        sys.exit(1)
    if not output_dir.is_dir():
        print(f"ERROR: output_dir is not a directory: {output_dir}", file=sys.stderr)
        sys.exit(1)

    emit(tasks_dir, output_dir, args.prefix, args.dry_run)


if __name__ == "__main__":
    main()

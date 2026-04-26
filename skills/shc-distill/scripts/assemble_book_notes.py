#!/usr/bin/env python3
"""Assemble book chapter notes from subagent task .output JSONL files.

For shc:distill large-book workflow. Each subagent task is launched against a
ch###_*.txt file extracted from an epub, and returns a markdown chapter note as
its final assistant message. This script:

  1. Walks the task .output directory (JSONL conversation logs).
  2. For each task, finds the prompt's `ch###_NAME.txt` filename — this is the
     ONLY trustworthy source of chapter ordering (do NOT parse the H1 of the
     output, formats vary across runs).
  3. Extracts the LAST assistant text message as the chapter note body.
  4. Writes each note to {dest_dir}/{prefix}-Ch{NN}-{slug}.md, with Ch00 reserved
     for the prologue (smallest ch### index in the set).

Usage:
    uv run python3 assemble_book_notes.py TASKS_DIR DEST_DIR FILENAME_PREFIX [--use-h1]

Example:
    uv run python3 assemble_book_notes.py \\
        /private/tmp/claude-501/.../tasks \\
        /Users/me/notes/Reeves-Wiedeman \\
        2026-04-Billion-Dollar-Loser --use-h1

The --use-h1 flag reads chapter numbers from the H1 header '# Ch{N}: {Title}'
in each subagent's output, instead of deriving them from epub txt file indices.
This avoids chapter number offset when epub files include non-content chapters
(dedication, TOC, etc.) before the first real chapter.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys


def strip_preamble(text: str) -> str:
    """Remove any content before the first markdown heading (# )."""
    for i, line in enumerate(text.splitlines()):
        if line.startswith("# "):
            return "\n".join(text.splitlines()[i:])
    return text


def clean_html_entities(text: str) -> str:
    """Decode the HTML entities sonnet subagents routinely emit despite prompts.

    Subagents (especially sonnet) reliably output `&gt;`, `&lt;`, `&amp;` inside
    blockquotes and <details> blocks even when explicitly told to use raw chars.
    This is a persistent, documented failure mode — fix it here so every
    assemble run produces clean markdown without needing post-hoc sed cleanup.

    Order matters: decode `&amp;` LAST to avoid double-decoding sequences like
    `&amp;gt;` → `&gt;` → `>`.
    """
    return (
        text
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&apos;", "'")
        .replace("&amp;", "&")
    )


def slugify(s: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[\s_]+", "-", s)
    return s[:max_len]


def parse_task_output(path: str) -> tuple[str, str]:
    """Return (first_user_text, last_assistant_text) from a JSONL task output."""
    first_user = ""
    last_assistant = ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            t = obj.get("type")
            msg = obj.get("message", {})
            # Fallback: newer JSONL format (isSidechain agents) puts role
            # inside message.role, not at the top level.
            if t is None:
                t = msg.get("role")
            content = msg.get("content", [])
            if t == "user" and not first_user:
                if isinstance(content, str):
                    first_user = content
                elif isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            first_user = c.get("text", "")
                            break
                    else:
                        first_user = json.dumps(content)[:4000]
            if t == "assistant":
                if isinstance(content, list):
                    parts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    if parts:
                        last_assistant = "\n".join(parts)
                elif isinstance(content, str):
                    last_assistant = content
    return first_user, last_assistant


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tasks_dir", help="Directory containing *.output JSONL files")
    ap.add_argument("dest_dir", help="Destination directory for chapter .md files")
    ap.add_argument("prefix", help="Filename prefix, e.g. 2026-04-Billion-Dollar-Loser")
    ap.add_argument(
        "--min-text",
        type=int,
        default=500,
        help="Minimum character count for a valid assistant reply (default 500)",
    )
    ap.add_argument(
        "--prologue-name",
        default="Prologue",
        help="Tag for the lowest-index chapter (default 'Prologue')",
    )
    ap.add_argument(
        "--use-h1",
        action="store_true",
        default=False,
        help="Parse '# Ch{N}: {Title}' from output H1 for chapter number and name "
             "(instead of deriving from epub txt filename index)",
    )
    ap.add_argument(
        "--pattern",
        default=r"ch(\d{3})_(.+?)\.txt",
        help="Regex to match in subagent prompt (first_user). Group 1 = chapter/segment "
             "number; Group 2 (optional) = name. Default matches epub 'ch###_NAME.txt'. "
             r"For video segments use e.g. 'batch_(\d+)\.txt'.",
    )
    args = ap.parse_args()

    if not os.path.isdir(args.tasks_dir):
        print(f"error: tasks_dir not found: {args.tasks_dir}", file=sys.stderr)
        return 2
    os.makedirs(args.dest_dir, exist_ok=True)

    # Phase 1: collect (chapter_idx, raw_name, text) from all tasks.
    raw_records: list[tuple[int, str, str]] = []
    skipped: list[tuple[str, str]] = []
    for fp in sorted(glob.glob(os.path.join(args.tasks_dir, "*.output"))):
        first, text = parse_task_output(fp)
        if not text or len(text) < args.min_text:
            skipped.append((os.path.basename(fp), f"text<{args.min_text}"))
            continue
        m = re.search(args.pattern, first)
        if not m:
            skipped.append((os.path.basename(fp), f"pattern {args.pattern!r} not matched in prompt"))
            continue
        groups = m.groups()
        idx = int(groups[0])
        raw_name = (groups[1] if len(groups) >= 2 and groups[1] else "").replace("_", " ").strip()
        raw_records.append((idx, raw_name, text))

    if not raw_records:
        print("error: no usable task outputs found", file=sys.stderr)
        return 1

    # Phase 2: assign chapter numbers.
    # --use-h1 mode: parse `# Ch{N}: {Title}` from the output H1 line.
    # Default mode: normalize by subtracting the minimum epub index (lowest → 0).
    use_h1 = getattr(args, "use_h1", False)
    by_chapter: dict[int, tuple[str, str]] = {}

    if use_h1:
        _min_idx = min(r[0] for r in raw_records)
        # Accept both Ch{N} (per-chapter) and Seg{N} (multi-chapter segment) H1s.
        # Seg is used when epub chapters are coarse XHTML blobs each containing
        # several book chapters and subagents emit one segment note per blob.
        h1_tags: dict[int, str] = {}
        for idx, raw_name, text in raw_records:
            clean = strip_preamble(text)
            sections = re.split(r"(?=^#\s+(?:Ch|Seg)\d+:)", clean, flags=re.MULTILINE)
            sections = [s.strip() for s in sections if s.strip()]
            matched_any = False
            for section in sections:
                h1_match = re.match(r"^#\s+(Ch|Seg)(\d+):\s*(.+)", section)
                if h1_match:
                    kind = h1_match.group(1)
                    num = int(h1_match.group(2))
                    name = h1_match.group(3).strip()
                    # Namespace Seg keys separately from Ch to avoid collisions.
                    key = num + 10000 if kind == "Seg" else num
                    matched_any = True
                    if key in by_chapter and len(by_chapter[key][1]) >= len(section):
                        continue
                    by_chapter[key] = (name, section)
                    h1_tags[key] = f"{kind}{num}"
            if not matched_any:
                # Fallback: no valid H1 found, use epub index offset
                num = idx - _min_idx
                name = re.sub(r"^Chapter\s+[\w-]+\s*", "", raw_name, flags=re.I).strip() or raw_name
                if num in by_chapter and len(by_chapter[num][1]) >= len(text):
                    continue
                by_chapter[num] = (name, text)
    else:
        min_idx = min(r[0] for r in raw_records)
        for idx, raw_name, text in raw_records:
            num = idx - min_idx
            # Strip "Chapter One" / "Chapter Twenty-Four" prefix from raw filename name.
            name = re.sub(r"^Chapter\s+[\w-]+\s*", "", raw_name, flags=re.I).strip()
            if not name:
                name = raw_name
            # Prefer the longest text on collision (likely the most complete).
            if num in by_chapter and len(by_chapter[num][1]) >= len(text):
                continue
            by_chapter[num] = (name, text)

    # Phase 3: write files.
    written: list[str] = []
    h1_tags = locals().get("h1_tags", {})
    for num in sorted(by_chapter):
        name, text = by_chapter[num]
        if num == 0 and not use_h1:
            ch_tag = f"Ch00-{args.prologue_name}"
            slug = ""
        elif num in h1_tags:
            ch_tag = h1_tags[num]
            slug = slugify(name)
        else:
            ch_tag = f"Ch{num}"
            slug = slugify(name)
        fname = f"{args.prefix}-{ch_tag}"
        if slug:
            fname += f"-{slug}"
        fname += ".md"
        out = os.path.join(args.dest_dir, fname)
        clean_text = clean_html_entities(strip_preamble(text))
        with open(out, "w", encoding="utf-8") as f:
            f.write(clean_text)
        if not clean_text.startswith("# "):
            print(f"  WARNING: {fname} does not start with '# ' after preamble strip")
        written.append(fname)

    print("WRITTEN:")
    for w in written:
        print(f"  {w}")
    print(f"total: {len(written)}")
    if skipped:
        print("SKIPPED:")
        for name, reason in skipped:
            print(f"  {name}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

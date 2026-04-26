#!/usr/bin/env python3
"""Extract translated SRT batches from subagent task .output JSONL files.

For shc:distill subtitle translation workflow. Each translation subagent
returns the translated SRT content as its final assistant message. This script:

  1. Scans *.output JSONL files in TASKS_DIR for prompts containing VIDEO_ID.
  2. Identifies batch number from the prompt (e.g. _en_batch_3.srt).
  3. Extracts the SRT entries from the last assistant text (strips intro/confirmation).
  4. Writes each batch to {DEST_DIR}/{VIDEO_ID}_{TARGET_LANG}_batch_{N}.srt.
  5. Validates entry counts and prints a summary with spot-check samples.

Usage:
    uv run python3 extract_translated_batches.py TASKS_DIR DEST_DIR VIDEO_ID [TARGET_LANG]

Example:
    uv run python3 extract_translated_batches.py \\
        /private/tmp/claude-501/.../tasks \\
        /Users/me/notes/Naval-Ravikant \\
        RqcKsR_mq14 \\
        zh
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys


def parse_task_output(path: str) -> tuple[str, list[str]]:
    """Return (first_user_text, all_assistant_texts) from a JSONL task output.

    Collects ALL assistant messages to handle subagents that hit output limits
    and produce multiple responses (each containing partial SRT content).
    """
    first_user = ""
    assistant_texts: list[str] = []
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
            content = msg.get("content", [])
            if t == "user" and not first_user:
                if isinstance(content, str):
                    first_user = content
                elif isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            first_user = c.get("text", "")
                            break
            if t == "assistant":
                if isinstance(content, list):
                    parts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    if parts:
                        assistant_texts.append("\n".join(parts))
                elif isinstance(content, str) and content:
                    assistant_texts.append(content)
    return first_user, assistant_texts


# Meta-text patterns that sonnet subagents emit around self-corrections.
# If these appear, we strip them so the surrounding SRT-looking text doesn't
# get polluted, and we rely on last-wins below to let the corrected entries win.
META_TEXT_PATTERNS = [
    # Self-correction prefaces
    r"I (?:realize|notice|see)[^\n]{0,250}?[Ll]et me (?:provide|give|re-?do|correct)[^\n]*\n",
    r"Looking at (?:the|my)[^\n]{0,100}?(?:again|error|mistake)[^\n]*\n",
    r"(?:Wait|Hmm|Actually)[,.][^\n]{0,200}?[\n]",
    # Chinese self-correction prefaces
    r"整理好的完整\s*SRT[^\n]*\n",
    r"(?:以下是|以下為)[^\n]{0,50}(?:修正|正確|完整|重新)[^\n]*\n",
    r"我(?:發現|注意到)[^\n]{0,100}(?:錯誤|問題|偏移)[^\n]*\n",
    # Markdown fences
    r"```(?:srt)?\s*\n",
    r"\n```\s*",
    # Instruction/outro noise
    r"(?:翻譯完成|完整的\s*SRT|corrected complete translation)[^\n]*\n",
]


def _strip_meta_text(text: str) -> str:
    """Remove subagent self-correction prefaces so raw SRT content survives."""
    for p in META_TEXT_PATTERNS:
        text = re.sub(p, "", text, flags=re.IGNORECASE)
    return text


def extract_srt_entries_deduped(texts: list[str]) -> dict[int, tuple[str, str]]:
    """Extract SRT entries from ALL assistant texts, deduplicated by entry number.

    Returns {entry_num: (timestamp_line, text_content)} keeping LAST occurrence.

    Why last-wins (not first-wins):
      Sonnet subagents sometimes emit an initial draft followed by a corrected
      pass ("I realize I'm making errors... Let me provide the corrected...")
      where the corrected pass re-outputs a subset of entries. First-wins would
      keep the buggy draft; last-wins picks up the correction. For the normal
      "output hit the limit, continue in msg 2" case the two halves don't
      overlap, so the choice is equivalent.

    Handles: code fence markers, meta-text prefaces, multiple assistant
    messages, entry self-corrections, overlapping entries.
    """
    entries: dict[int, tuple[str, str]] = {}
    for text in texts:
        # Clean code fence markers and self-correction prefaces
        text = re.sub(r" *```(?:srt)? *", "", text)
        text = _strip_meta_text(text)
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if (
                re.match(r"^\d+$", stripped)
                and i + 1 < len(lines)
                and "-->" in lines[i + 1]
            ):
                num = int(stripped)
                ts = lines[i + 1].strip()
                text_lines = []
                k = i + 2
                while k < len(lines) and lines[k].strip() and not (
                    re.match(r"^\d+$", lines[k].strip())
                    and k + 1 < len(lines)
                    and "-->" in lines[k + 1]
                ):
                    text_lines.append(lines[k])
                    k += 1
                # last-wins: later occurrence overrides earlier draft
                entries[num] = (ts, "\n".join(text_lines))
                i = k
            else:
                i += 1
    return entries


def entries_to_srt(entries: dict[int, tuple[str, str]]) -> str:
    """Convert entries dict to SRT text, sorted by entry number."""
    parts = []
    for num in sorted(entries):
        ts, text = entries[num]
        parts.append(f"{num}\n{ts}\n{text}\n")
    return "\n".join(parts) + "\n" if parts else ""


def count_srt_entries(text: str) -> int:
    """Count SRT entries by counting bare number lines followed by timestamp lines."""
    count = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^\d+$", line.strip()) and i + 1 < len(lines):
            if "-->" in lines[i + 1]:
                count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tasks_dir", help="Directory containing *.output JSONL files")
    ap.add_argument("dest_dir", help="Destination directory for batch .srt files")
    ap.add_argument("video_id", help="VIDEO_ID to filter relevant tasks")
    ap.add_argument(
        "target_lang", nargs="?", default="zh", help="Target language (default: zh)"
    )
    args = ap.parse_args()

    source_lang = "en" if args.target_lang == "zh" else "zh"

    if not os.path.isdir(args.tasks_dir):
        print(f"error: tasks_dir not found: {args.tasks_dir}", file=sys.stderr)
        return 2
    os.makedirs(args.dest_dir, exist_ok=True)

    # Phase 1: find relevant task outputs and extract batch info.
    batches: dict[int, dict[int, tuple[str, str]]] = {}  # batch_num -> entries
    skipped: list[tuple[str, str]] = []

    for fp in sorted(glob.glob(os.path.join(args.tasks_dir, "*.output"))):
        prompt, texts = parse_task_output(fp)
        if not prompt or args.video_id not in prompt:
            continue  # Not a task for this VIDEO_ID
        if not texts:
            skipped.append((os.path.basename(fp), "no assistant messages"))
            continue

        # Identify batch number from prompt (batch or gap) — match any extension
        m = re.search(r"(?:batch|gap)_(\d+)\.", prompt)
        if not m:
            skipped.append((os.path.basename(fp), "no batch/gap_N in prompt"))
            continue
        batch_num = int(m.group(1))

        entries = extract_srt_entries_deduped(texts)
        if not entries:
            skipped.append((os.path.basename(fp), "no SRT entries found in output"))
            continue

        # Merge entries into existing batch (gap files fill in missing entries)
        if batch_num in batches:
            for num, val in entries.items():
                batches[batch_num].setdefault(num, val)
        else:
            batches[batch_num] = entries

    if not batches:
        print(f"error: no translation tasks found for VIDEO_ID={args.video_id}", file=sys.stderr)
        return 1

    # Phase 2: write batch files and validate.
    total_entries = 0
    for batch_num in sorted(batches):
        entries = batches[batch_num]
        srt = entries_to_srt(entries)
        fname = f"{args.video_id}_{args.target_lang}_batch_{batch_num}.srt"
        out_path = os.path.join(args.dest_dir, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(srt)

        # Compare against source batch
        src_fname = f"{args.video_id}_{source_lang}_batch_{batch_num}.srt"
        src_path = os.path.join(args.dest_dir, src_fname)
        marker = ""
        if os.path.exists(src_path):
            src_count = count_srt_entries(open(src_path).read())
            if src_count != len(entries):
                marker = f"  ⚠️ 源檔 {src_count} → 譯檔 {len(entries)}，缺 {src_count - len(entries)} 條"

        total_entries += len(entries)
        print(f"  batch {batch_num}: {len(entries)} entries -> {fname}{marker}")

    print(f"\n提取完成：{len(batches)} 個批次，共 {total_entries} 條字幕")

    # Phase 3: spot-check the first and last batch.
    first_num = min(batches)
    last_num = max(batches)
    first_entries = batches[first_num]
    last_entries = batches[last_num]
    first_key = min(first_entries)
    last_key = max(last_entries)
    print(f"\n抽樣驗證:")
    ts1, txt1 = first_entries[first_key]
    print(f"  [head] {first_key} | {ts1} | {txt1[:60]}")
    tsN, txtN = last_entries[last_key]
    print(f"  [tail] {last_key} | {tsN} | {txtN[:60]}")

    if skipped:
        print("\nSKIPPED:")
        for name, reason in skipped:
            print(f"  {name}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

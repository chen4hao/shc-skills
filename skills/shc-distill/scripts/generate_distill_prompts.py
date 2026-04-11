#!/usr/bin/env python3
"""Generate subagent prompts and agent_config.json for shc:distill book workflow.

For the large-book distill workflow, this script replaces error-prone manual
prompt construction (where the main agent hand-writes 20+ near-identical
Agent prompts and inevitably introduces typos and format drift).

Inputs:
    CONFIG_JSON — a JSON file describing the book metadata and chapter list
    OUTPUT_DIR — directory that will receive prompt files and agent_config.json

Outputs:
    {OUTPUT_DIR}/prompt_ch{N}.txt    — one prompt per chapter
    {OUTPUT_DIR}/agent_config.json   — list of agent launch specs

The main agent workflow becomes:
    1. Run epub_extract.py --list + probe Copyright chapter to confirm author
    2. ensure_dir + epub_extract.py --chapters to extract main content
    3. Write _distill_template.md (shared template with format + rules)
    4. Write {output_dir}/book_config.json (book metadata + chapter list)
    5. Run generate_distill_prompts.py book_config.json {output_dir}
    6. Read {output_dir}/agent_config.json
    7. Fire all Agent() calls in one message from agent_config.json.agents[]
    8. Wait for notifications; meanwhile draft the summary note skeleton
    9. assemble_book_notes.py --use-h1 (HTML entity cleanup is now built-in)
   10. Fill in the summary note; cleanup_epub_txt.py

CONFIG_JSON format:
    {
      "book": {
        "title_en": "Coaching for Performance",
        "title_zh": "高績效教練",
        "edition": "5th Edition (2017)",
        "author": "Sir John Whitmore & Performance Consultants International",
        "source_type": "書籍章節",
        "author_bio": "Whitmore 是賽車冠軍出身、Tim Gallwey 『內在遊戲』歐洲推廣者、職場教練鼻祖"
      },
      "template_path": "/absolute/path/to/_distill_template.md",
      "extract_dir": "/absolute/path/to/_tmp_extract",
      "chapters": [
        {
          "num": 0,
          "en_title": "Introduction",
          "zh_title": "前言與引言",
          "txt_files": ["ch005_Foreword.txt", "ch007_Introduction.txt"],
          "size": "medium",
          "hint": "本章是引言，重點萃取..."
        },
        {
          "num": 1,
          "en_title": "What Is Coaching?",
          "zh_title": "什麼是教練法？",
          "txt_files": ["ch010_1_What_Is_Coaching_.txt"],
          "size": "large"
        }
      ]
    }

Size values:
    small  — chapter < 12KB: Key Takeaway 3-5 個, Key Quote 2-3 個
    medium — 12-20KB:        Key Takeaway 4-7 個, Key Quote 2-4 個
    large  — > 20KB:         Key Takeaway 可到 8-10 個, Key Quote 可到 5-8 個

Usage:
    uv run python3 generate_distill_prompts.py book_config.json {output_dir}
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SIZE_HINTS = {
    "small": "本章短（<12KB），Key Takeaway 3-5 個、Key Quote 2-3 個即可，不要硬擠 10 個",
    "medium": "本章中等，Key Takeaway 4-7 個、Key Quote 2-4 個即可",
    "large": "本章內容豐富，Key Takeaway 可到 8-10 個、Key Quote 可到 5-8 個",
}

PROMPT_TEMPLATE = """你是學習萃取專家。請為《{title_en}》({edition}) Ch{num} 撰寫萃取筆記。

**步驟**:
1. 用 Read 工具讀取 `{template_path}` 獲得完整格式要求（含禁用 HTML entity、禁前言後語、H1 格式、條件區塊適用性判斷等規則）
2. 用 Read 工具讀取{txt_clause}
3. 根據格式模板撰寫完整萃取筆記

**書籍資訊**（填入模板變數）:
- H1 必須為: `# Ch{num}: {en_title}`
- 第二行: `## {title_zh} — {zh_title}`
- 作者: {author}
- 來源類型: {source_type}
{author_bio_line}
**嚴格要求**（違反任一條就是格式失敗）:
- 所有輸出使用繁體中文（zh-TW），包括任何開頭和結尾文字
- 直接以 `# ` 標題開頭，禁止任何前言文字（禁止「以下是筆記」「所有章節已讀取」）
- 結尾停在最後一個 `</details>` 標籤後，禁止任何後語（禁止「萃取完成」）
- 禁用 HTML entity（不要 `&gt;` `&lt;` `&amp;`），blockquote 用原生 `>` 字元
- 禁止嘗試用 Write 工具或 Bash 寫入檔案（會被 sandbox 拒絕）
- 條件區塊（Call to Action / Mistakes / Unique Secret / Best Practice / Fun Story）素材不足完全省略，不要硬擠
- 作者引用他人的話不要歸為作者本人的觀點
- {size_hint}
{chapter_hint_block}
不要嘗試寫入檔案。將完整筆記直接作為回覆輸出。
"""


def build_txt_clause(txt_files: list[str], extract_dir: str) -> str:
    """Build the Read instruction clause for one or multiple txt files.

    Single file → inline: "`/path/to/file.txt` 整個檔案（不設 limit）"
    Multi file  → block form with bullet list, followed by a group directive.
    """
    if len(txt_files) == 1:
        return f" `{os.path.join(extract_dir, txt_files[0])}` 整個檔案（不設 limit）"
    lines = [" 以下所有檔案並將內容合併為本章:"]
    for t in txt_files:
        lines.append(f"   - `{os.path.join(extract_dir, t)}`")
    lines.append("   （每個檔案都讀完整，不設 limit）")
    return "\n".join(lines)


def build_chapter_hint_block(hint: str) -> str:
    """Build the optional chapter-specific hint block."""
    if not hint or not hint.strip():
        return ""
    return f"\n**章節重點提示**:\n{hint.strip()}\n"


def build_author_bio_line(bio: str) -> str:
    """Build the optional author-bio line."""
    if not bio or not bio.strip():
        return ""
    return f"- 作者背景: {bio.strip()}\n"


def build_description(num: int, en_title: str) -> str:
    """Build a short Agent description (max ~50 chars)."""
    # Strip punctuation that might cause issues and truncate
    short = "".join(c for c in en_title if c.isalnum() or c in " -")[:38].rstrip()
    return f"Distill Ch{num} {short}"


def build_prompt(book: dict, chapter: dict, template_path: str, extract_dir: str) -> str:
    """Build a single subagent prompt."""
    num = chapter["num"]
    size = chapter.get("size", "medium")
    if size not in SIZE_HINTS:
        print(
            f"warning: Ch{num} size={size!r} unknown, falling back to 'medium'",
            file=sys.stderr,
        )
        size = "medium"
    return PROMPT_TEMPLATE.format(
        title_en=book["title_en"],
        title_zh=book.get("title_zh", book["title_en"]),
        edition=book.get("edition", ""),
        author=book["author"],
        author_bio_line=build_author_bio_line(book.get("author_bio", "")),
        source_type=book.get("source_type", "書籍章節"),
        num=num,
        en_title=chapter["en_title"],
        zh_title=chapter.get("zh_title", chapter["en_title"]),
        template_path=template_path,
        txt_clause=build_txt_clause(chapter["txt_files"], extract_dir),
        size_hint=SIZE_HINTS[size],
        chapter_hint_block=build_chapter_hint_block(chapter.get("hint", "")),
    )


def validate_config(config: dict) -> list[str]:
    """Return a list of error messages; empty list means valid."""
    errors = []
    if "book" not in config:
        errors.append("missing 'book' key")
        return errors
    book = config["book"]
    for field in ("title_en", "author"):
        if field not in book or not book[field]:
            errors.append(f"book.{field} is required")
    if "template_path" not in config:
        errors.append("missing 'template_path' key")
    elif not os.path.isfile(config["template_path"]):
        errors.append(f"template_path not found: {config['template_path']}")
    if "extract_dir" not in config:
        errors.append("missing 'extract_dir' key")
    if "chapters" not in config or not config["chapters"]:
        errors.append("chapters list is empty or missing")
        return errors
    seen_nums = set()
    for i, ch in enumerate(config["chapters"]):
        prefix = f"chapters[{i}]"
        for field in ("num", "en_title", "txt_files"):
            if field not in ch:
                errors.append(f"{prefix}.{field} is required")
        if "num" in ch:
            if ch["num"] in seen_nums:
                errors.append(f"{prefix}.num={ch['num']} is duplicated")
            seen_nums.add(ch["num"])
        if "txt_files" in ch and not ch["txt_files"]:
            errors.append(f"{prefix}.txt_files is empty")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("config_json", help="Path to book config JSON")
    ap.add_argument("output_dir", help="Directory for prompt files and agent_config.json")
    args = ap.parse_args()

    if not os.path.isfile(args.config_json):
        print(f"error: config not found: {args.config_json}", file=sys.stderr)
        return 2

    with open(args.config_json, encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON in {args.config_json}: {e}", file=sys.stderr)
            return 2

    errors = validate_config(config)
    if errors:
        print("error: config validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    book = config["book"]
    template_path = config["template_path"]
    extract_dir = config["extract_dir"]
    chapters = config["chapters"]

    os.makedirs(args.output_dir, exist_ok=True)

    agents = []
    for ch in chapters:
        num = ch["num"]
        prompt = build_prompt(book, ch, template_path, extract_dir)
        prompt_filename = f"prompt_ch{num}.txt"
        prompt_path = os.path.join(args.output_dir, prompt_filename)
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        agents.append(
            {
                "chapter_num": num,
                "description": build_description(num, ch["en_title"]),
                "prompt_file": prompt_path,
                "agent_prompt": prompt,
                "agent_settings": {
                    "subagent_type": "general-purpose",
                    "model": "sonnet",
                    "mode": "dontAsk",
                    "run_in_background": True,
                },
            }
        )

    config_out = {
        "book_title": book["title_en"],
        "total_agents": len(agents),
        "agents": agents,
    }
    config_path = os.path.join(args.output_dir, "agent_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_out, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(agents)} agent prompts for {book['title_en']}")
    print(f"Prompt files: {args.output_dir}/prompt_ch*.txt")
    print(f"Agent config: {config_path}")
    print()
    print("Next steps for main agent:")
    print(f"  1. Read {config_path}")
    print("  2. For each entry in 'agents', fire ONE Agent() call with:")
    print("       description      = agent.description")
    print("       prompt           = agent.agent_prompt")
    print("       subagent_type    = agent.agent_settings.subagent_type")
    print("       model            = agent.agent_settings.model")
    print("       mode             = agent.agent_settings.mode")
    print("       run_in_background = agent.agent_settings.run_in_background")
    print("  3. All Agent() calls MUST be in the SAME message (parallel launch)")
    print("  4. While waiting, draft the summary note skeleton")
    print("  5. After all complete, run assemble_book_notes.py --use-h1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

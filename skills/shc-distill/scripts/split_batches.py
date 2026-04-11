"""拆分 SRT 字幕為多個批次（可選擇產出翻譯 prompt 或純分段）。

用法: uv run python3 split_batches.py <INPUT_SRT> <OUTPUT_DIR> <VIDEO_ID> [NUM_BATCHES] [LANG] [options]

位置參數:
  INPUT_SRT:     清理後的 SRT 檔案路徑
  OUTPUT_DIR:    批次檔案輸出目錄（子代理可存取的專案目錄）
  VIDEO_ID:      影片 ID（用於批次檔名前綴，避免並行會話覆蓋）
  NUM_BATCHES:   批次數量（預設 8，每批 ~300 條避免子代理撞輸出上限）
  LANG:          來源語言前綴（預設 "en"，中文原文影片用 "zh"）

選項:
  --split-by {entry,time}  拆分方式（預設 entry）
                           entry: 按條目數均分（每批 ~total/N 條，可能時段不均）
                           time:  按總時長均分（每批 ~total_dur/N 秒，時段一致、條目不均）
  --split-only             只產 batch SRT 檔，不產翻譯 prompt 和 agent_config.json
                           用於純分段萃取流程（如影片 distill 分段）

產出：
  {VIDEO_ID}_{LANG}_batch_{N}.srt   — 各批次 SRT 檔（一律產出）
  {VIDEO_ID}_prompt_batch_{N}.txt   — 各批次翻譯 prompt（僅在非 --split-only）
  {VIDEO_ID}_agent_config.json      — Agent 啟動設定（僅在非 --split-only）
"""
import re, os, sys, math, json, argparse

# ── Prompt 模板 ──────────────────────────────────────────────

PROMPT_EN_TO_ZH = """\
你是專業字幕翻譯專家。請將英文 SRT 字幕翻譯為繁體中文（zh-TW）。
所有輸出必須使用繁體中文（zh-TW），包括任何開頭和結尾文字。

## 嚴格規則（違反任何一條即為失敗）：
1. **條目數量必須完全相同** — 輸入 {entry_count} 條，輸出必須恰好 {entry_count} 條。禁止拆分或合併條目。
2. **保留完全相同的條目編號和時間戳** — 僅替換文字行
3. **每條字幕的中文必須對應同一條英文的語意** — 這是雙語同步的關鍵

## 翻譯品質要求：
- 翻譯自然流暢，符合中文口語習慣，非逐字翻譯
- 專有名詞（人名、公司名、技術名詞）保留原文
- 中文每行控制在 25 字以內，超過可適當精簡
- 參考前後 2-3 條字幕的語境來翻譯，確保上下文連貫

## 輸出格式：
嚴格遵循 SRT 格式，每個區塊之間用一個空行分隔：

1
00:00:01,000 --> 00:00:04,500
翻譯文字

2
00:00:05,200 --> 00:00:08,800
翻譯文字

請用 Read 工具讀取 {srt_path} **整個檔案**，翻譯所有 {entry_count} 條字幕。

**重要：不要嘗試用 Write 工具或 Bash 寫入檔案（會被 sandbox 拒絕）。請將完整翻譯後的 SRT 內容直接作為你的回覆輸出，由主代理負責寫入。**

**格式要求：直接輸出純 SRT 文字，禁止用 ``` code block 包裝（code fence 標記會污染最終字幕檔）。**

翻譯完成後回報：輸入條目數={entry_count}，輸出條目數=?，確認一致。"""

PROMPT_ZH_TO_EN = """\
You are a professional subtitle translator. Translate Traditional Chinese (zh-TW) SRT subtitles to English.
All output must be in English.

## Strict Rules (violating any rule = failure):
1. **Entry count must be exactly the same** — Input has {entry_count} entries, output must have exactly {entry_count} entries. No splitting or merging.
2. **Keep identical entry numbers and timestamps** — Only replace the text lines.
3. **Each subtitle's English must correspond to the same Chinese entry's meaning** — Critical for bilingual sync.

## Translation quality:
- Natural, fluent English (not word-by-word translation)
- Proper nouns (names, companies, technical terms) keep original form
- Keep each line under 60 characters
- Reference surrounding 2-3 subtitles for context continuity

## Output format:
Strict SRT format, one blank line between blocks:

1
00:00:01,000 --> 00:00:04,500
Translated text

2
00:00:05,200 --> 00:00:08,800
Translated text

Use the Read tool to read {srt_path} **entire file**, translate all {entry_count} entries.

**IMPORTANT: Do NOT use Write tool or Bash to write files (will be rejected by sandbox). Output the complete translated SRT content directly as your reply. The main agent will handle writing.**

**Format: Output plain SRT text only. Do NOT wrap in ``` code blocks (code fence markers will pollute the final subtitle file).**

After translation, report: input entries={entry_count}, output entries=?, confirm they match."""

# 子代理的 meta-prompt：告訴子代理去讀 prompt 檔案
META_PROMPT = """\
你是字幕翻譯子代理。請用 Read 工具讀取下方的 prompt 檔案，其中包含完整的翻譯任務說明和要翻譯的 SRT 檔案路徑。讀取後嚴格遵循其中的所有指示完成翻譯任務。

Prompt 檔案路徑：{prompt_path}"""


# ── 拆分函式 ───────────────────────────────────────────────

def _parse_srt_time(ts):
    """Parse SRT timestamp 'HH:MM:SS,mmm' to seconds (float)."""
    ts = ts.strip()
    h, m, rest = ts.split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _block_time(block, which='start'):
    """Extract start or end time (seconds) from an SRT block."""
    for line in block.strip().split('\n'):
        if '-->' in line:
            parts = line.split('-->')
            return _parse_srt_time(parts[0 if which == 'start' else 1])
    return 0.0


def split_by_entry(blocks, num_batches):
    """按條目數均分：每批 ~total/N 條（原始做法）。"""
    total = len(blocks)
    per_batch = math.ceil(total / num_batches)
    return [blocks[i * per_batch:(i + 1) * per_batch] for i in range(num_batches)]


def split_by_time(blocks, num_batches):
    """按總時長均分：每批 ~total_dur/N 秒，時段一致但條目數可能不均。"""
    if not blocks:
        return [[] for _ in range(num_batches)]

    total_dur = _block_time(blocks[-1], 'end')
    if total_dur <= 0:
        return split_by_entry(blocks, num_batches)

    seg_dur = total_dur / num_batches
    batches = [[] for _ in range(num_batches)]
    for b in blocks:
        bs = _block_time(b, 'start')
        seg_idx = min(int(bs / seg_dur), num_batches - 1)
        batches[seg_idx].append(b)
    return batches


# ── 主邏輯 ───────────────────────────────────────────────────

def split_srt(input_path, output_dir, video_id, num_batches=8, lang="en",
              split_by="entry", split_only=False):
    with open(input_path) as f:
        content = f.read()
    blocks = [b.strip() for b in re.split(r'\n\n+', content.strip()) if '-->' in b]
    total = len(blocks)

    # 依 split_by 選擇拆分方式
    if split_by == "time":
        split_blocks = split_by_time(blocks, num_batches)
    else:
        split_blocks = split_by_entry(blocks, num_batches)

    # 翻譯方向（僅在非 --split-only 時使用）
    if lang == "en":
        target_lang = "zh"
        prompt_template = PROMPT_EN_TO_ZH
        direction = "EN→ZH"
        direction_desc = "EN → ZH（英文翻譯為繁體中文）"
    else:
        target_lang = "en"
        prompt_template = PROMPT_ZH_TO_EN
        direction = "ZH→EN"
        direction_desc = "ZH → EN（中文翻譯為英文）"

    batches_info = []

    for i, batch in enumerate(split_blocks):
        if not batch:
            continue
        batch_num = i + 1

        # 寫入批次 SRT 檔（一律產出）
        srt_path = os.path.join(output_dir, f"{video_id}_{lang}_batch_{batch_num}.srt")
        with open(srt_path, 'w') as f:
            for block in batch:
                f.write(f"{block}\n\n")

        # 顯示批次資訊（含時間範圍）
        if batch:
            ts_start = _block_time(batch[0], 'start')
            ts_end = _block_time(batch[-1], 'end')
            time_info = f"[{int(ts_start // 60):02d}:{int(ts_start % 60):02d}–{int(ts_end // 60):02d}:{int(ts_end % 60):02d}]"
        else:
            time_info = ""
        print(f"  Batch {batch_num}: {len(batch)} entries {time_info} -> {os.path.basename(srt_path)}")

        # --split-only: 只產 SRT 檔，跳過 prompt 產生
        if split_only:
            continue

        # 產出完整子代理 prompt
        prompt_text = prompt_template.format(
            entry_count=len(batch),
            srt_path=srt_path,
        )
        prompt_path = os.path.join(output_dir, f"{video_id}_prompt_batch_{batch_num}.txt")
        with open(prompt_path, 'w') as f:
            f.write(prompt_text)

        # 產出 meta-prompt（子代理實際收到的 prompt）
        meta_prompt = META_PROMPT.format(prompt_path=prompt_path)

        batches_info.append({
            "batch_num": batch_num,
            "entry_count": len(batch),
            "srt_file": srt_path,
            "prompt_file": prompt_path,
            "description": f"Translate SRT batch {batch_num} {direction}",
            "agent_prompt": meta_prompt,
        })

    non_empty = sum(1 for b in split_blocks if b)

    # --split-only: 收尾訊息
    if split_only:
        print(f"\n[--split-only] 拆分完成：{total} 條字幕 → {non_empty} 個批次（{split_by}-based，不產 prompt）")
        print(f"  批次檔：{output_dir}/{video_id}_{lang}_batch_*.srt")
        return

    # Write agent config JSON
    config = {
        "video_id": video_id,
        "source_lang": lang,
        "target_lang": target_lang,
        "direction": direction_desc,
        "total_entries": total,
        "num_batches": len(batches_info),
        "split_by": split_by,
        "agent_settings": {
            "model": "sonnet",
            "mode": "dontAsk",
            "run_in_background": True,
        },
        "batches": batches_info,
    }
    config_path = os.path.join(output_dir, f"{video_id}_agent_config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # phase-specific 提醒
    print(f"\n拆分完成：{total} 條字幕 → {len(batches_info)} 個批次（{direction_desc}，{split_by}-based）")
    print("════════════════════════════════════════════════════════")
    print(f"⚠️  下一步：在【同一個訊息】中啟動全部 {len(batches_info)} 個 Agent")
    print(f"   設定檔（含各批次 prompt 路徑）：{config_path}")
    print(f"   Agent 設定：model=\"sonnet\", mode=\"dontAsk\", run_in_background=true")
    print(f"")
    print(f"   做法：Read agent_config.json → 對每個 batch 發一個 Agent call")
    print(f"         每個 Agent 的 prompt = batch.agent_prompt（已預產出）")
    print(f"         所有 {len(batches_info)} 個 Agent call 必須在同一個回覆中發出")
    print("════════════════════════════════════════════════════════")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input_srt")
    ap.add_argument("output_dir")
    ap.add_argument("video_id")
    # 位置參數 NUM_BATCHES 和 LANG 保留為可選 nargs="?"，維持舊呼叫介面
    ap.add_argument("num_batches", nargs="?", type=int, default=8,
                    help="Number of batches (default 8)")
    ap.add_argument("lang", nargs="?", choices=["en", "zh"], default="en",
                    help="Source language prefix (default en)")
    ap.add_argument("--split-by", choices=["entry", "time"], default="entry",
                    help="Split method (default: entry)")
    ap.add_argument("--split-only", action="store_true",
                    help="Only produce batch SRT files, skip translation prompt generation")
    args = ap.parse_args()

    split_srt(
        args.input_srt,
        args.output_dir,
        args.video_id,
        num_batches=args.num_batches,
        lang=args.lang,
        split_by=args.split_by,
        split_only=args.split_only,
    )


if __name__ == "__main__":
    main()

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
  --auto-batches           依條目數自動選擇批次數（覆蓋 NUM_BATCHES 位置參數）
                           ≤450 條 → 2-3 批（跳過 sample-first 門檻，可一次性同訊息啟動）
                           450-1200 條 → 每批 ~200 條
                           >1200 條 → 每批 ~250 條
  --glossary PATH          指向主代理寫好的詞彙表 .md 檔（產品名保留清單、統一中譯表、
                           常見字幕誤聽變體還原表）。腳本讀取後附加到每個
                           prompt_batch_N.txt 的末尾，取代「主代理在每個 Agent call
                           手工貼同一份還原表」的 DRY 反模式。

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
4. **人名一律保留原文拼字** — 不論出現在 speaker label（方括號內）或正文中，所有人名（first name、last name、honorifics）保留原文不音譯。範例：`Ro Khanna` 保留 `Ro Khanna`，**禁止**譯為「甘納」「坎納」等音譯；`H.R. McMaster` 保留 `H.R. McMaster`，**禁止**譯為「麥馬斯特」。**唯一例外**是擁有通用正式中譯的名字（例：`Jensen Huang → 黃仁勳` 可接受）。跨 batch 翻譯一致性的關鍵就在這條——子代理間對「什麼算通用中譯」的判斷分歧會產生混用譯名
5. **Speaker label 格式統一用全形【】** — 所有 speaker 標記一律用全形 `【】`，**禁止**用半形 `[]`。即使原 SRT 使用半形 `[`/`]`，翻譯時也統一改為全形。範例：輸入 `[JENSEN HUANG]` → 輸出 `【JENSEN HUANG】` ✓、保留 `[JENSEN HUANG]` ✗。跨 batch 格式一致的關鍵
6. **Speaker label 內的人名即使看起來錯誤也不自行糾正** — 若原 SRT speaker label 的人名與 description/title 提到的講者不匹配（可能是 YouTube auto-caption 的 speaker diarization 誤識別），**保留原字不替換**——修正由主代理在 finalize 後統一處理。範例：若原 SRT 出現 `[GERALD CONNOLLY]` 但 description 只列 Ro Khanna，子代理**保留** `【GERALD CONNOLLY】`（僅做格式統一），不自行改為 `【RO KHANNA】`

## 翻譯品質要求：
- 翻譯自然流暢，符合中文口語習慣，非逐字翻譯
- 公司名、技術名詞保留原文（人名規則見嚴格規則第 4 條）
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

## 自我修正上限（強制規則）：
- 完成第一輪完整翻譯後，若發現錯誤，**最多**做一次整體修正並重新輸出完整版
- **嚴禁**反覆自我懷疑、重讀原檔、重譯部分條目、累計超過 2 輪自我修正——這會導致子代理耗時暴增（實測曾達正常批次的 8-20 倍）
- 若第一輪翻譯自覺不準，用「修正版」取代「原版」作為最終輸出，不要兩版都保留
- 主代理 extract 腳本會用**最後一個** assistant message 作為權威版本，所以只要確保最後輸出是完整正確的就好

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

## Self-correction cap (mandatory):
- After your first complete translation, if you find errors, do **at most one** holistic correction and re-output the complete version
- **Forbidden**: repeated self-doubt, re-reading the source, re-translating partial entries, or accumulating >2 rounds of self-correction. This causes subagent runtime to explode (observed cases: 8-20× normal batch time)
- If your first pass feels inaccurate, replace it with a corrected version as the final output. Do not keep both versions
- The main-agent extractor treats the **last** assistant message as authoritative, so just make sure the last output is complete and correct

After translation, report: input entries={entry_count}, output entries=?, confirm they match."""

# 子代理的 meta-prompt：告訴子代理去讀 prompt 檔案
META_PROMPT = """\
你是字幕翻譯子代理。請用 Read 工具讀取下方的 prompt 檔案，其中包含完整的翻譯任務說明和要翻譯的 SRT 檔案路徑。讀取後嚴格遵循其中的所有指示完成翻譯任務。

Prompt 檔案路徑：{prompt_path}"""

# 末段 batch 特別警告：附加在最後一個 non-empty batch 的 prompt 末尾。
# 末段 SRT 含 outro/applause/感謝詞，子代理常見故障是把連續兩個 EN 條目合併
# 翻譯到一個 ZH 條目（即使語意流暢也算違規），導致 ZH 比 EN 少 1 條，最終
# cascade 偏移觸發 finalize 的 outro drift 偵測。
# 來源：2026-04-30 Karpathy × Sequoia distill — batch 3 把 entry 349 (gain
# insight) + 350 (synthetic data generation) 合併翻譯，導致 entry 349-359 共
# 11 條 ZH 偏移 -1，需要手寫 patch_drift_349_359.py 修復。
OUTRO_WARNING = """\

---

## ⚠️ 末段 batch 特別警告（最後一個 batch 專用）

本批次為**最後一個 batch**，包含影片 outro / 感謝詞 / [applause] 等收尾條目。
SRT 末段子代理常見故障：把連續兩個 EN 條目合併翻譯到一個 ZH 條目（即使語意
流暢也算違規），導致下游 ZH 比 EN 少 1 條，cascade 偏移整段。

### 強制 1:1 對齊規則（違反即為失敗）

- **每個 EN 條目必須獨立翻譯為一個 ZH 條目**——禁止合併兩個 EN 條目到一個
  ZH 條目，即使 EN 條目語意連續、跨句、跨段也禁止
- 出現 `[applause]` / `[laughter]` / `[music]` 等註解條目，獨立保留為
  `[掌聲]` / `[笑聲]` / `[音樂]`，不與相鄰條目合併
- 末段最後 5-15 條尤其容易出錯——逐條對照原 EN 條目編號和時間戳，**不要憑
  語感分段**
- 範例違規（曾發生）：EN 條目 N = "I'm excited to be back here..."、EN 條目
  N+1 = "actually take care of understanding... thank you so much for joining
  us"。**禁止**把這兩條合併翻譯到 ZH 條目 N，即使「我期待幾年後回來看
  agent 是否也接管了理解。非常感謝...」更通順——必須拆成 ZH 條目 N 和
  N+1，分別對應原 EN 條目時間戳

違反此規則會觸發 finalize 的 outro drift 偵測，需要手寫 patch script 修復
末段 5-15 條，多 3-4 個訊息輪次的成本。
"""


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


# ── 自動批次數選擇 ────────────────────────────────────────

def auto_num_batches(total_entries: int) -> int:
    """依條目數自動選擇批次數。

    目標優先順序：
    1. 能用 ≤3 批就用 ≤3 批（跳過 sample-first 規則，可同訊息一次性啟動）
    2. 每批 ≤ ~200 條（避免 sonnet 輸出截斷）
    3. 總批次控制在合理範圍（避免主代理認知負擔）

    決策表：
    - ≤450 條 → 2-3 批（每批 ~150 條）：跳過 sample-first
    - 450-1200 條 → 3-6 批（每批 ~200 條）
    - >1200 條 → 5+ 批（每批 ~250 條）
    """
    if total_entries <= 450:
        return max(2, math.ceil(total_entries / 150))
    if total_entries <= 1200:
        return math.ceil(total_entries / 200)
    return math.ceil(total_entries / 250)


# ── 主邏輯 ───────────────────────────────────────────────────

def split_srt(input_path, output_dir, video_id, num_batches=8, lang="en",
              split_by="entry", split_only=False, auto_batches=False,
              glossary_text=""):
    # 自動偵測 .clean.srt 變體：若傳入未清理的 .srt 且同目錄存在 .clean.srt，自動切換
    # 避免錯用未清理的 YouTube 自動字幕（2370 raw vs 513 final 條目數差異巨大）
    if not input_path.endswith('.clean.srt') and input_path.endswith('.srt'):
        clean_candidate = input_path[:-4] + '.clean.srt'
        if os.path.exists(clean_candidate):
            print(
                f"  [auto] {os.path.basename(input_path)} 同目錄存在 .clean.srt 變體，"
                f"改用 {os.path.basename(clean_candidate)}（dedup 後的乾淨版）",
                file=sys.stderr,
            )
            input_path = clean_candidate

    with open(input_path) as f:
        content = f.read()
    blocks = [b.strip() for b in re.split(r'\n\n+', content.strip()) if '-->' in b]
    total = len(blocks)

    if auto_batches:
        auto_n = auto_num_batches(total)
        print(f"  [auto] {total} entries → {auto_n} batches (overriding default {num_batches})")
        num_batches = auto_n

    # 標記翻譯主軌：在 INPUT_SRT 同目錄建 master_{lang}.srt symlink，
    # 讓下游 merge.py 能精確抓到「翻譯所根據的那一份英文」，而非誤用
    # 同目錄的 .en-orig.clean.srt 等候選。
    try:
        input_abs = os.path.abspath(input_path)
        master_link = os.path.join(os.path.dirname(input_abs), f"master_{lang}.srt")
        if os.path.islink(master_link) or os.path.exists(master_link):
            os.remove(master_link)
        os.symlink(input_abs, master_link)
    except OSError:
        # symlink 失敗（例如 Windows / 某些 fs）就靜默跳過——
        # merge.py 有精確 glob fallback，不會選錯
        pass

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

    # 找最後一個 non-empty batch number — outro warning 只附加在末段 batch
    # 防止子代理把連續 EN 條目合併到一個 ZH 條目（cascade 偏移觸發 outro drift）
    last_non_empty_batch_num = max(
        (i + 1 for i, b in enumerate(split_blocks) if b),
        default=0
    )

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
        is_last = batch_num == last_non_empty_batch_num
        last_marker = " [outro warning attached]" if is_last and not split_only else ""
        print(f"  Batch {batch_num}: {len(batch)} entries {time_info} -> {os.path.basename(srt_path)}{last_marker}")

        # --split-only: 只產 SRT 檔，跳過 prompt 產生
        if split_only:
            continue

        # 產出完整子代理 prompt
        prompt_text = prompt_template.format(
            entry_count=len(batch),
            srt_path=srt_path,
        )
        # 附加主代理提供的 glossary（產品名保留 / 統一中譯 / 誤聽還原表）
        # 取代「主代理在每個 Agent call 手工貼同一份還原表」的反模式
        if glossary_text:
            prompt_text += (
                "\n\n---\n\n"
                "## 主代理注入的詞彙表（絕對強制，禁止質疑）\n\n"
                + glossary_text.strip()
                + "\n"
            )

        # 末段 batch 特別警告：強化 1:1 條目對齊，預防 outro drift
        # （見 OUTRO_WARNING 模組級註解；2026-04-30 Karpathy distill 來源）
        if is_last:
            prompt_text += "\n" + OUTRO_WARNING
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
    n = len(batches_info)
    print(f"\n拆分完成：{total} 條字幕 → {n} 個批次（{direction_desc}，{split_by}-based）")
    print("════════════════════════════════════════════════════════")
    if n <= 3:
        print(f"⚠️  ≤3 批 → 跳過 sample-first，一次性同訊息啟動")
        print(f"")
        print(f"   下一訊息【同一個回覆內】併發：")
        print(f"     - {n} 個 Agent call（batch 1..{n}，每個 run_in_background=true）")
        print(f"     - Read head 500 + Read tail 200（SRT 主代理筆記素材）")
        print(f"     - advisor()  ← 與 agents 零資料依賴，必須同訊息並行")
        print(f"   總計 {n + 3} 個工具同訊息並行")
    else:
        print(f"⚠️  ≥4 批 → 觸發 sample-first 流程（分 2 個訊息）")
        print(f"")
        print(f"   訊息 2：batch 1 Agent + Read head 500 + Read tail 200（同訊息並行）")
        print(f"")
        print(f"   訊息 3（batch 1 驗證通過後）：【同一個回覆內】併發")
        print(f"     - {n - 1} 個 Agent call（batch 2..{n}，每個 run_in_background=true）")
        print(f"     - advisor()  ← 禁止拖到 batch 全回傳後單獨 call")
        print(f"   總計 {n} 個工具同訊息並行")
        print(f"")
        print(f"   違規高危：只發 {n - 1} 個 Agent 漏掉 advisor → 損失 ~60s 並行窗口")
    print(f"")
    print(f"   Agent 設定：model=\"sonnet\", mode=\"dontAsk\", run_in_background=true")
    print(f"   Agent prompt：讀 {video_id}_prompt_batch_N.txt 中的翻譯指示")
    print(f"   （不需要 Read {video_id}_agent_config.json，meta-prompt 格式可推得）")
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
    ap.add_argument("--auto-batches", action="store_true",
                    help="Auto-select NUM_BATCHES by entry count (≤450→2-3 batches, ≤1200→~200/batch, else ~250/batch). Overrides NUM_BATCHES positional.")
    ap.add_argument("--glossary", default=None,
                    help="Path to a .md file containing the main agent's glossary (product-name preservation list, unified translations, mishearing restoration table). Content is appended to every prompt_batch_N.txt, replacing the DRY-violating pattern of hand-pasting the same glossary into each Agent call.")
    args = ap.parse_args()

    glossary_text = ""
    if args.glossary:
        try:
            with open(args.glossary, encoding="utf-8") as f:
                glossary_text = f.read()
            print(f"  [glossary] loaded {len(glossary_text)} chars from {args.glossary}",
                  file=sys.stderr)
        except OSError as e:
            print(f"  WARN: could not read glossary {args.glossary}: {e}",
                  file=sys.stderr)

    split_srt(
        args.input_srt,
        args.output_dir,
        args.video_id,
        num_batches=args.num_batches,
        lang=args.lang,
        split_by=args.split_by,
        split_only=args.split_only,
        auto_batches=args.auto_batches,
        glossary_text=glossary_text,
    )


if __name__ == "__main__":
    main()

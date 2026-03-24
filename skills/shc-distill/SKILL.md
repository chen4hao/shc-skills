---
name: shc-distill
description: >
  萃取網路文章、訪談、演講、影片、podcast 的學習重點精華，整理成結構化 markdown 筆記並儲存。
  當來源為訪談影片或 podcast 時，會自動擷取完整字幕並存為三個 SRT 字幕檔：英文(*.en.srt)、繁體中文(*.zh-tw.srt)、中英雙語(*.en&cht.srt)。
  當使用者提供 URL 並要求萃取重點、整理筆記、提取學習精華、summarize key takeaways 時觸發。
  Use when user shares a URL and wants to extract insights, distill key takeaways,
  summarize learnings, or create study notes from articles, interviews, talks,
  videos, podcasts, essays, or blog posts. When the source is an interview video
  or podcast, automatically extracts and saves three SRT subtitle files: English
  (*.en.srt), Traditional Chinese (*.zh-tw.srt), and bilingual (*.en&cht.srt).
---

# 學習萃取專家 | Distill

**觸發條件**：使用者提供 URL 並要求萃取重點、整理筆記、提取學習精華。
**關鍵字**：distill, 萃取, 整理筆記, summarize, key takeaways, 學習重點

## 你的角色

* 你是一名學習專家，熟悉不同領域的專業，擅長掌握事物的本質重點，能引導新手輕易地理解各種主題概念並學習新知技能。
* 使用者是一個對各種事物、主題充滿好奇心的學習者，希望能夠透過網路影片、訪談、演講、文章來學習各種知識及技能。
* 為了能「更好、更有效地學習」各種知識技能，解決無知無能的焦慮。
* 核心學習方法：直接從各領域專家的第一手訪談、演講、文章等內容學習，並從中萃取出重點精華。

## 處理流程

1. **取得內容**：使用 WebFetch 取得使用者提供的 URL 的完整內容。若內容過長或需要更多細節，進行第二次 fetch 聚焦於引用語句、數據、故事等細節。
2. **字幕擷取**（條件步驟）：若來源是影片或 podcast 的訪談/對話內容，執行字幕擷取流程（見下方「字幕擷取規則」）。**必須**產出三個 SRT 字幕檔：`.en.srt`（英文）、`.zh-tw.srt`（繁體中文）、`.en&cht.srt`（中英雙語）。完整流程：下載 → 去重 → 翻譯補全 → 合併 → 驗證。
3. **適用性評估**：通讀全文後，先判斷每個輸出區塊是否有足夠素材（見下方「區塊適用性判斷」）。
4. **深度萃取**：根據下方的輸出格式，對每個適用區塊進行深度分析並萃取內容精華。
5. **輸出結果**：依序輸出所有適用區塊，省略不適用的區塊。
6. **儲存檔案**：將完整輸出儲存為 markdown 檔案（見下方儲存規則）。若步驟 2 有產生 SRT 字幕檔，在輸出末尾附上字幕檔路徑。

## 區塊適用性判斷

每個區塊在輸出前必須先評估內容是否有足夠素材支撐。區塊分為兩類：

**必要區塊**（所有內容類型都必須輸出）：
- Key Takeaway
- Key Quote
- One Page Infograph Outline

**條件區塊**（僅在內容中有明確相關素材時才輸出）：
- Call to Action — 需有明確可操作的建議或機會
- Best Practice — 需有講者/作者的第一手經驗或實際做法
- Unique Secret — 需有與主流觀點明確不同的看法
- Fun Story — 需有具體的故事或軼事

**判斷規則**：
- 若條件區塊的素材不足（少於 2 個有品質的項目），則**完全省略該區塊**，不要輸出區塊標題
- **嚴禁硬擠**：不要為了湊數而把不相關或太勉強的內容塞進區塊
- 寧可少輸出一個區塊，也不要輸出低品質的內容

## 影音與字幕擷取規則

本步驟僅在來源為**影片（YouTube 等）或 podcast 的訪談/對話內容**時執行。純文字文章跳過此步驟。

**最終目標**：
1. 將影片/音訊下載至本地備存
2. 產出**三個 SRT 字幕檔**——這是**硬性要求**：
   - `*.en.srt` — 純英文字幕
   - `*.zh-tw.srt` — 純繁體中文字幕
   - `*.en&cht.srt` — 中英雙語字幕（每條字幕兩行：英文在上、繁體中文在下）

### 判斷邏輯

```
URL 是否為影片/podcast？
├─ 否 → 跳過，繼續適用性評估
└─ 是 → 內容是否為訪談/對話/演講？
    ├─ 否（純音樂、短片） → 跳過
    └─ 是 → 執行下載 + 字幕擷取
```

**判斷影片/podcast 的依據**：
- URL 包含 `youtube.com`、`youtu.be`、`podcasts.apple.com`、`open.spotify.com`、`podcasts.google.com`
- URL 來自已知影片/podcast 平台
- 使用者明確提到「影片」「訪談」「podcast」「演講」

### 重要：Bash 指令執行規則

為避免權限系統阻擋，執行 Bash 指令時遵守以下規則：
- **禁止使用複合命令**（`&&`、`||`、`;`、`|`）串接不同工具。每個工具呼叫應獨立發出。
  - ❌ `sleep 10 && yt-dlp ...`
  - ❌ `cd /tmp && for f in *.vtt; do ffmpeg ...; done`
  - ✅ 先 `sleep 10`，再另外呼叫 `yt-dlp ...`
- **禁止使用 shell 重導向**（`2>&1`、`2>/dev/null`、`> file`）——重導向中的 `>` `&` 會導致權限 glob 模式無法匹配。Bash 工具已自動捕獲 stdout 和 stderr，不需要重導向。
  - ❌ `yt-dlp ... 2>&1`
  - ❌ `ls -la /tmp/ 2>/dev/null`
  - ✅ `yt-dlp ...`（不加任何重導向）
  - 若需要 `cat a.srt b.srt > output.srt` 這類輸出重導向，改用 Python 腳本或 Write 工具替代
- **禁止使用 `cd` 開頭的命令**——`cd` 不在已允許清單中，且 Bash 工具會重設工作目錄。一律使用絕對路徑。
  - ❌ `cd /tmp/distill-subs && ls`
  - ✅ `ls /tmp/distill-subs/`
- **禁止使用 `for`/`while` 等 shell 迴圈**——改用 Python 腳本或多個獨立的 Bash 呼叫
- **禁止使用 ffmpeg**——dedup.py 已能處理 VTT 和 SRT，不需要額外轉檔
- **禁止在命令參數中使用方括號 `[` `]`**——方括號是 glob 特殊字元，會導致權限模式匹配失敗。yt-dlp 的格式篩選用 `-S`（format sort）替代 `-f "...[height<=720]..."` 語法。
  - ❌ `-f "bestvideo[height<=720]+bestaudio"`
  - ✅ `-S "height:720" -f "bv+ba/ba/best"`
- **禁止在命令參數中使用小括號 `(` `)`**——小括號會被權限系統誤判為 `Bash(...)` 語法的邊界，導致模式匹配失敗。yt-dlp 的 `%(id)s.%(ext)s` 輸出模板含有 `()`，因此 **yt-dlp 必須透過 Python 腳本呼叫**（見步驟 A），不可直接在 Bash 中執行。
  - ❌ `yt-dlp -o "/tmp/distill-subs/%(id)s.%(ext)s" "$URL"`
  - ✅ 寫入 download.py，用 `uv run python3 /tmp/distill-subs/download.py` 執行
- **禁止使用 bash `grep`**——改用內建 Grep 工具或 Python 腳本。bash grep 的 regex 參數常含 `[` `]` `(` `)` `*` `$` 等 glob 特殊字元，會導致權限匹配失敗。
  - ❌ `grep -c "^[0-9]*$" file.srt`
  - ✅ 使用 Grep 工具，或用 Python 腳本統計
- **不要發出不必要的 yt-dlp 呼叫**——步驟 A 的單次呼叫已包含所有需要的下載。不要用 `--print filename` 或 `--skip-download` 等額外呼叫
- **可以**在同一訊息中平行發出多個獨立的 Bash 呼叫
- **暫存目錄寫入**：所有往 `/tmp/distill-subs/` 寫入檔案的操作，**必須使用 `python3 -c '...'` 方式寫入**，不可使用 Write 工具。外層用單引號 `'...'`、內層用雙引號 `"..."` 和三引號 `"""..."""`。這是為了利用已有的 `Bash(python3 -c *)` 廣域許可，避免需要 `Write(/tmp/...)` 路徑權限。
  - **重要**：暫存目錄的 Python 腳本中**禁止使用 ASCII 單引號（`'`）**，一律改用雙引號，以確保外層單引號包裹不會斷開。
- **暫存目錄讀取**：所有從 `/tmp/distill-subs/` 讀取檔案的操作，使用 `cat`、`head` 或 `tail` 命令而非 Read 工具。子代理（`bypassPermissions` 模式）不受此限。
- **暫存目錄清理**：使用 `python3 -c "import shutil; shutil.rmtree('/tmp/distill-subs', True)"` 而非 `rm -rf`。這是為了利用 `Bash(python3 -c *)` 權限，避免需要多條 `rm` 路徑權限。

### 擷取流程

#### 步驟 A：下載影音檔 + 英文字幕（單次 yt-dlp 呼叫）

**關鍵**：只呼叫一次 yt-dlp，同時下載影音檔和**僅英文**字幕。不下載中文自動字幕（原因：步驟 C 一律從英文翻譯為中文，中文自動字幕不會被使用，且下載中文字幕常觸發 YouTube 429 限流導致整個下載中斷）。

用一個 `python3 -c` 命令同時建立暫存目錄並寫入下載腳本（**重要**：不可直接在 Bash 中執行 yt-dlp，因為 `%(id)s.%(ext)s` 的小括號會導致權限匹配失敗）：

```bash
python3 -c '
import os
os.makedirs("/tmp/distill-subs", exist_ok=True)
with open("/tmp/distill-subs/download.py", "w") as f:
    f.write("""import subprocess, sys

url = sys.argv[1]
subprocess.run([
    "yt-dlp",
    "--cookies-from-browser", "chrome",
    "--write-subs", "--write-auto-subs",
    "--sub-langs", "en-orig,en",
    "--convert-subs", "srt",
    "-S", "height:720",
    "-f", "bv+ba/ba/best",
    "--merge-output-format", "mp4",
    "-o", "/tmp/distill-subs/%(id)s.%(ext)s",
    url
], check=True)
""")
'
```

> **為何預設使用 cookies**：YouTube 越來越頻繁地要求身份驗證（bot check），不帶 cookies 的 yt-dlp 會直接失敗。`--cookies-from-browser chrome` 從本機 Chrome 瀏覽器讀取已登入的 cookies，繞過 bot check。首次執行時 macOS 可能會彈出鑰匙圈存取授權，同意後後續不再詢問。

用 Bash 執行下載：
```bash
uv run python3 /tmp/distill-subs/download.py "$URL"
```

下載完成後，用 Bash 檢查結果：
```bash
ls /tmp/distill-subs/
```

> **下載格式說明**：預設優先下載影片（720p 以下 + 最佳音訊，合併為 mp4）。若平台僅提供音訊（如純 podcast），會自動降級為 m4a 音訊格式。

> **VTT vs SRT**：`--convert-subs "srt"` 會自動將 VTT 轉為 SRT。若 yt-dlp 因中途錯誤而只產出 `.vtt` 檔，**不需要額外用 ffmpeg 轉檔**——步驟 B 的 dedup.py 已能直接處理 VTT 和 SRT 兩種格式。

#### 步驟 B：去重清理（必須執行）

YouTube 自動字幕使用漸進式顯示（progressive display），造成兩種重複：(1) 條目間重複——後面的條目包含前面的文字；(2) 條目內重複——同一條目的文字自身有重複片段。用 Python 腳本進行四階段清理：Phase 1 條目間去重、Phase 2 條目內去重、Phase 3 新文字提取、Phase 4 重新切割為自然語句字幕。同時解碼 HTML 實體（`&gt;` → `>`）並移除 `>>` 講者標記。

> **重要**：dedup.py **同時支援 VTT 和 SRT 輸入格式**，不需要事先用 ffmpeg 或其他工具轉檔。直接對 yt-dlp 下載的檔案執行即可。

**重要**：為避免權限提示，使用 `python3 -c` 將腳本寫入檔案，再用 Bash 執行。

**步驟 B-1**：用 `python3 -c` 將以下 Python 腳本寫入 `/tmp/distill-subs/dedup.py`。寫入方式：`python3 -c 'with open("/tmp/distill-subs/dedup.py","w") as f: f.write("""...下方完整腳本...""")'`：

```python
import re, html, glob

def clean_srt(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 支援 VTT 和 SRT：移除 VTT header 和樣式標籤
    content = re.sub(r'^WEBVTT\n.*?\n\n', '', content, flags=re.DOTALL)
    content = re.sub(r' align:\w+ position:\d+%', '', content)
    content = re.sub(r'<[^>]+>', '', content)

    blocks = re.split(r'\n\n+', content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        ts_line = None
        text_lines = []
        for line in lines:
            if '-->' in line:
                ts_line = line.strip().replace('.', ',')
            elif ts_line is not None:
                clean = line.strip()
                if clean and not clean.startswith('Kind:') and not clean.startswith('Language:'):
                    text_lines.append(clean)
        if ts_line and text_lines:
            text = ' '.join(text_lines)
            # === 清理 HTML 實體和講者標記 ===
            text = html.unescape(text)           # &gt; → >, &amp; → &, etc.
            text = text.replace('>>', ' ')        # YouTube 講者切換標記
            text = re.sub(r'(?:^|\s)>\s', ' ', text)  # 單獨的 > 標記
            text = re.sub(r'\s+', ' ', text).strip()
            m = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', ts_line)
            if m and text:
                entries.append({'start': m.group(1), 'end': m.group(2), 'text': text})

    if not entries:
        print(f"  {input_path}: 0 entries (empty)")
        return

    # === Phase 1：漸進式去重（條目間） ===
    # YouTube 自動字幕的多個連續條目中，後者包含前者的文字
    merged = []
    i = 0
    while i < len(entries):
        current = entries[i]
        j = i + 1
        while j < len(entries) and j < i + 4:
            if current['text'] in entries[j]['text']:
                current = entries[j]
                j += 1
            elif entries[j]['text'] in current['text']:
                j += 1
            else:
                break
        merged.append(current)
        i = j

    deduped = [merged[0]]
    for e in merged[1:]:
        if e['text'] != deduped[-1]['text']:
            deduped.append(e)

    # === Phase 2：條目內去重 ===
    # YouTube 漸進式顯示造成同一條目內文字重複，例如：
    # "A B C D E D E F G F G H" → 清理為 "A B C D E F G H"
    # 演算法：逐詞掃描，若當前位置起的 k 個詞與已收集文字的末尾 k 個詞相同，則跳過
    def dedup_intra(text):
        words = text.split()
        if len(words) < 6:
            return text
        clean = []
        i = 0
        while i < len(words):
            found_repeat = False
            if len(clean) >= 3:
                max_k = min(len(words) - i, len(clean))
                for k in range(max_k, 2, -1):
                    if words[i:i+k] == clean[-k:]:
                        i += k
                        found_repeat = True
                        break
            if not found_repeat:
                clean.append(words[i])
                i += 1
        return ' '.join(clean)

    for e in deduped:
        e['text'] = dedup_intra(e['text'])

    # === Phase 3：條目間新文字提取 ===
    # 找出每個條目相對於前一條目的「真正新增的文字」
    # 使用後綴-前綴匹配：找前一條目文字的最長後綴 == 當前條目文字的前綴
    prev_words = []
    segments = []
    for e in deduped:
        curr_words = e['text'].split()
        best_overlap = 0
        for k in range(min(len(prev_words), len(curr_words)), 0, -1):
            if prev_words[-k:] == curr_words[:k]:
                best_overlap = k
                break
        new_words = curr_words[best_overlap:] if best_overlap > 0 else curr_words
        if new_words:
            segments.append({
                'start': e['start'],
                'end': e['end'],
                'text': ' '.join(new_words)
            })
        prev_words = curr_words

    if not segments:
        segments = deduped

    # === Phase 4：合併為自然語句字幕區塊 ===
    # 改進：以句子邊界為主要切分依據，時長和詞數為輔助上限
    # 目標：每個字幕是一個完整語句，3-6 秒、最多 25 個詞
    def ts_to_ms(ts):
        h, m, rest = ts.split(':')
        s, ms = rest.split(',')
        return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)

    # 句末標點（強切分點）
    SENTENCE_END = re.compile(r'[.!?]["\'）\)»]*$')
    # 子句標點（弱切分點：逗號、分號、冒號、破折號後）
    CLAUSE_BREAK = re.compile(r'[,;:\-–—]$')

    final = []
    buf_text = []
    buf_start = segments[0]['start']
    buf_end = segments[0]['end']
    buf_words = 0
    for seg in segments:
        seg_words = len(seg['text'].split())
        buf_text.append(seg['text'])
        buf_end = seg['end']
        buf_words += seg_words
        combined = ' '.join(buf_text)
        duration = ts_to_ms(buf_end) - ts_to_ms(buf_start)
        last_word = combined.rstrip().split()[-1] if combined.strip() else ''

        is_sentence_end = bool(SENTENCE_END.search(last_word))
        is_clause_break = bool(CLAUSE_BREAK.search(last_word))

        # 切分條件（依優先順序）：
        should_split = (
            (duration >= 2000 and is_sentence_end) or   # 2秒+ 句末 → 立即切
            duration >= 6000 or                          # 6 秒硬上限
            (duration >= 3500 and is_clause_break) or    # 3.5秒+ 子句斷點 → 切
            (duration >= 4000 and buf_words >= 12) or    # 4秒+ 且夠長 → 切
            buf_words >= 25                              # 25 詞硬上限
        )
        if should_split:
            final.append({'start': buf_start, 'end': buf_end, 'text': combined})
            buf_text = []
            buf_start = seg['end']
            buf_words = 0
    if buf_text:
        final.append({'start': buf_start, 'end': buf_end, 'text': ' '.join(buf_text)})

    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, e in enumerate(final, 1):
            f.write(f"{idx}\n{e['start']} --> {e['end']}\n{e['text']}\n\n")

    print(f"  {input_path}: {len(entries)} raw → {len(deduped)} deduped → {len(final)} final")

for f in sorted(glob.glob('/tmp/distill-subs/*.*')):
    if f.endswith(('.srt', '.vtt')):
        out = re.sub(r'\.(srt|vtt)$', '.clean.srt', f)
        clean_srt(f, out)
```

**步驟 B-2**：用 Bash 執行腳本：
```bash
uv run python3 /tmp/distill-subs/dedup.py
```

執行後，清理過的檔案存為 `*.clean.srt`。確認至少有一個英文 `.clean.srt` 檔。

#### 步驟 C：翻譯為雙語（子代理並行翻譯）

**核心策略：永遠以英文字幕為主軌（master track），翻譯產生中文字幕。**

YouTube 不同語言的自動字幕各自獨立分段，條目數量和時間切分都不同，直接合併必然導致中英文錯位。因此**一律使用英文清理後的字幕作為唯一來源**，透過翻譯產生對應的中文字幕，確保每一條英文都有精確對應的中文。

| 已取得 | 處理方式 |
|--------|----------|
| 英文 `.clean.srt` 存在 | **忽略中文自動字幕**，一律透過子代理翻譯英文 → 中文 |
| 僅中文 `.clean.srt` | **必須翻譯為英文**（見下方子代理翻譯流程） |
| 都沒有 | 標記失敗，繼續萃取流程 |

##### 子代理並行翻譯流程

字幕翻譯會嚴重污染主 context window，因此**必須委派給子代理**處理。使用 **sonnet 模型**以節省成本並加速。

**流程**：

1. 用 Read 工具讀取清理後的 SRT，計算總條目數 N
2. 將 N 條字幕分為 4-6 個批次（每批約 100 條），計算每批的起始行號
3. 用 **Agent 工具**一次性啟動所有批次的子代理（在同一個訊息中發出多個 Agent 呼叫），每個子代理：
   - `model: "sonnet"` — 使用 sonnet 模型節省成本
   - `mode: "bypassPermissions"` — 避免子代理卡在權限確認
   - `run_in_background: true` — 背景執行，並行處理
   - 任務：讀取指定行範圍的英文 SRT，翻譯為繁體中文，寫入對應的批次檔案

**子代理 prompt 範本**（以英翻中為例）：
```
你是專業字幕翻譯專家。請將英文 SRT 字幕翻譯為繁體中文（zh-TW）。

## 嚴格規則（違反任何一條即為失敗）：
1. **條目數量必須完全相同** — 輸入 N 條，輸出必須恰好 N 條。禁止拆分或合併條目。
2. **保留完全相同的條目編號和時間戳** — 僅替換文字行
3. **每條字幕的中文必須對應同一條英文的語意** — 這是雙語同步的關鍵

## 翻譯品質要求：
- 翻譯自然流暢，符合中文口語習慣，非逐字翻譯
- 專有名詞（人名、公司名、技術名詞）保留原文
- 中文每行控制在 25 字以內，超過可適當精簡
- 參考前後 2-3 條字幕的語境來翻譯，確保上下文連貫

## 輸出格式：
嚴格遵循 SRT 格式，每個區塊之間用一個空行分隔：
```
1
00:00:01,000 --> 00:00:04,500
翻譯文字

2
00:00:05,200 --> 00:00:08,800
翻譯文字
```

請用 Read 工具讀取 /tmp/distill-subs/{英文clean檔名}，
行範圍：offset={起始行} limit={行數}，
然後翻譯並用 Write 工具寫入 /tmp/distill-subs/zh_batch_{X}.srt。

完成後，回報輸入和輸出的條目數量，確認一致。
```

4. 等待所有子代理完成（系統會自動通知）
5. 用 Python 將所有批次檔案依序合併為完整的中文 SRT（避免使用 `>` 重導向）：
```bash
uv run python3 -c "import glob; open('/tmp/distill-subs/zh.combined.srt','w').write(''.join(open(f).read() for f in sorted(glob.glob('/tmp/distill-subs/zh_batch_*.srt'))))"
```

**翻譯規則**（已寫入子代理 prompt 中）：
- 保留**完全相同的時間戳、序號和條目數量**（1:1 對應是雙語同步的關鍵）
- 翻譯時保持語句自然流暢，非逐字翻譯
- 參考前後文上下文翻譯，確保語意連貫
- 專有名詞（人名、公司名、技術名詞）保留原文
- 中文每行控制在 25 字以內

**嚴禁**：在主 context 中逐批翻譯。**嚴禁**跳過翻譯步驟。

#### 步驟 D：產出三個版本的 SRT 字幕檔

本步驟產出三個字幕檔：純英文、純中文、中英雙語。

**重要**：為避免權限提示，使用 `python3 -c` 將腳本寫入檔案，再用 Bash 執行。

**步驟 D-1**：用 `python3 -c` 將以下 Python 腳本寫入 `/tmp/distill-subs/merge.py`。寫入方式：`python3 -c 'with open("/tmp/distill-subs/merge.py","w") as f: f.write("""...下方完整腳本...""")'`：

```python
import re, glob

def parse_srt(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    entries = []
    for block in re.split(r'\n\n+', content.strip()):
        lines = block.strip().split('\n')
        ts_line = None
        text_lines = []
        for line in lines:
            if '-->' in line:
                ts_line = line.strip()
            elif ts_line is not None:
                clean = line.strip()
                if clean and not clean.isdigit():
                    text_lines.append(clean)
        if ts_line and text_lines:
            text = ' '.join(text_lines)
            m = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', ts_line)
            if m:
                entries.append({'ts': ts_line, 'text': text,
                                'start': ts_to_ms(m.group(1)), 'end': ts_to_ms(m.group(2))})
    return entries

def ts_to_ms(ts):
    h, m, rest = ts.split(':')
    s, ms = rest.split(',')
    return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)

def write_srt(path, entries_list, mode='single'):
    """寫入 SRT 檔案。mode: 'single' 寫單行文字, 'bilingual' 寫雙行(en+zh)"""
    with open(path, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(entries_list):
            if mode == 'bilingual':
                ts, en_text, zh_text = item
                f.write(f"{idx + 1}\n{ts}\n{en_text}\n{zh_text}\n\n")
            else:
                ts, text = item
                f.write(f"{idx + 1}\n{ts}\n{text}\n\n")
    print(f"  {path}: {len(entries_list)} entries")

en_files = sorted(glob.glob('/tmp/distill-subs/*.en*.clean.srt') + glob.glob('/tmp/distill-subs/*.en-orig*.clean.srt'))
zh_files = glob.glob('/tmp/distill-subs/zh.combined.srt')
if not zh_files:
    zh_files = sorted(glob.glob('/tmp/distill-subs/*.zh*.clean.srt'))

if not en_files:
    print("ERROR: No English SRT found"); exit(1)
if not zh_files:
    print("ERROR: No Chinese SRT found"); exit(1)

en_entries = parse_srt(en_files[0])
zh_entries = parse_srt(zh_files[0])
print(f"English: {len(en_entries)} entries, Chinese: {len(zh_entries)} entries")

# === 對齊策略：以英文為主軌 ===
# 情況 1：條目數量一致（翻譯流程正確時應如此）→ 直接 1:1 對應
# 情況 2：條目數量不一致 → 用時間戳重疊對齊
paired = []  # [(ts, en_text, zh_text), ...]

if len(en_entries) == len(zh_entries):
    print("條目數量一致，使用 1:1 對應")
    for i, en in enumerate(en_entries):
        paired.append((en['ts'], en['text'], zh_entries[i]['text']))
else:
    print(f"條目數量不一致（EN={len(en_entries)}, ZH={len(zh_entries)}），使用時間戳對齊")
    for en in en_entries:
        best_zh = '（翻譯缺失）'
        best_overlap = 0
        for zh in zh_entries:
            overlap_start = max(en['start'], zh['start'])
            overlap_end = min(en['end'], zh['end'])
            overlap = max(0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_zh = zh['text']
        paired.append((en['ts'], en['text'], best_zh))

# === 產出三個檔案 ===
print("產出三個 SRT 字幕檔：")
write_srt('/tmp/distill-subs/en.srt',      [(ts, en) for ts, en, zh in paired])
write_srt('/tmp/distill-subs/zh-tw.srt',    [(ts, zh) for ts, en, zh in paired])
write_srt('/tmp/distill-subs/bilingual.srt', paired, mode='bilingual')
print("完成！")
```

**步驟 D-2**：用 Bash 執行腳本：
```bash
uv run python3 /tmp/distill-subs/merge.py
```

產出的三個檔案格式：

**en.srt**（純英文）：
```
1
00:00:01,000 --> 00:00:04,500
Hello, welcome to today's interview.
```

**zh-tw.srt**（純中文）：
```
1
00:00:01,000 --> 00:00:04,500
你好，歡迎來到今天的訪談。
```

**bilingual.srt**（中英雙語，英文在上）：
```
1
00:00:01,000 --> 00:00:04,500
Hello, welcome to today's interview.
你好，歡迎來到今天的訪談。
```

#### 步驟 E：複製影音檔和字幕到最終位置

**重要**：所有檔案的主檔名必須相同（例如主檔名為 `2026-03-Interview-with-Sam-Altman`，則產出 `.en.srt`、`.zh-tw.srt`、`.en&cht.srt`、`.mp4`）。

每個檔案複製獨立發出一個 Bash 呼叫，避免複合命令：

```bash
# 呼叫 1：複製英文字幕
cp /tmp/distill-subs/en.srt "{儲存目錄}/{檔案名稱前綴}.en.srt"
```

```bash
# 呼叫 2：複製中文字幕
cp /tmp/distill-subs/zh-tw.srt "{儲存目錄}/{檔案名稱前綴}.zh-tw.srt"
```

```bash
# 呼叫 3：複製雙語字幕
cp /tmp/distill-subs/bilingual.srt "{儲存目錄}/{檔案名稱前綴}.en&cht.srt"
```

```bash
# 呼叫 4：複製影音檔（先用 ls 查看 /tmp/distill-subs/ 確認副檔名，再選擇對應指令）
# 優先 mp4，其次 m4a、webm
cp /tmp/distill-subs/{影片ID}.mp4 "{儲存目錄}/{檔案名稱前綴}.mp4"
```

驗證要點（用 `head` 和 `tail` 命令抽查 `*.en&cht.srt` 開頭、中段、結尾各 10 條）：
- 序號從 1 開始連續遞增
- 時間戳格式為 `HH:MM:SS,mmm`（**逗號**分隔毫秒）
- 雙語檔每個字幕區塊恰好**兩行文字**（第一行英文、第二行繁體中文）
- **中英文語意對應**：抽查 3-5 條確認中文確實是英文的翻譯，而非錯位的無關內容
- 英文檔和中文檔每個區塊各只有**一行文字**
- 三個字幕檔的條目數量必須完全相同
- 區塊之間用一個空行分隔
- 所有檔案在同一目錄，且主檔名相同

### SRT 字幕檔儲存規則

產出**三個 SRT 字幕檔** + **影音檔**，與 markdown 筆記存放在**相同目錄**下：

範例：
```
{作者或來源名稱}/
├── 2026-03-Interview-with-Sam-Altman.md              ← 萃取筆記
├── 2026-03-Interview-with-Sam-Altman.en.srt          ← 英文字幕
├── 2026-03-Interview-with-Sam-Altman.zh-tw.srt       ← 繁體中文字幕
├── 2026-03-Interview-with-Sam-Altman.en&cht.srt      ← 中英雙語字幕（en 在上）
└── 2026-03-Interview-with-Sam-Altman.mp4             ← 影片檔（與字幕同主檔名）
```

> **檔案命名規則**：所有檔案共用相同主檔名，字幕副檔名分別為 `.en.srt`、`.zh-tw.srt`、`.en&cht.srt`，影音副檔名依實際格式而定（`.mp4` 為影片、`.m4a` 為音訊）。

### 失敗處理

**分級降級**（必須按順序嘗試，禁止直接跳到最低級）：

1. **目標**：三個 SRT 字幕檔（`.en.srt` + `.zh-tw.srt` + `.en&cht.srt`）+ 影音檔
2. **降級 1**：若中文翻譯在子代理處理中累積錯誤過多，仍然產出三個 SRT 檔並在輸出末尾註明翻譯品質問題
3. **降級 2**：若連英文字幕都下載失敗（yt-dlp 完全無法取得任何字幕），在輸出末尾附上：`> 字幕擷取：未成功 — {原因}`
4. **降級 3**：若影音下載失敗但字幕成功，仍然產出字幕檔，在輸出末尾註明影音下載失敗
5. **不阻擋後續的萃取流程**，繼續進行適用性評估和深度萃取

**嚴禁**：因為中文字幕下載失敗就直接放棄雙語目標。必須走子代理翻譯補全流程。

### 清理暫存檔

流程結束後，刪除 `/tmp/distill-subs/` 整個暫存目錄（影音檔已複製到最終位置）：
```bash
python3 -c "import shutil; shutil.rmtree('/tmp/distill-subs', True)"
```

---

## 儲存規則

將完整的萃取結果儲存為 markdown 檔案，遵循以下慣例：

- **儲存位置**：`{作者或來源名稱}/{檔案名稱}.md`（相對於使用者指定的輸出目錄或當前工作目錄）
- **目錄命名**：以作者名稱或來源名稱建立資料夾（英文用連字號分隔，例如 `Matt-Shumer`；中文直接使用，例如 `簡立峰`）
- **檔案命名**：`{年份}-{月份}-{簡短標題}.md`，例如 `2026-02-Something-Big-is-Happening.md`
- 若資料夾不存在，先建立資料夾
- 檔案開頭包含 metadata 區塊
- 所有輸出使用繁體中文（zh-TW），原文引用保留原語言並附翻譯

### Markdown 檔案結構範本

```markdown
# {文章/演講標題}

> **作者**：{作者全名} — {一句話背景介紹，如職稱或代表作}
> **發布日期**：{YYYY-MM-DD 或 YYYY-MM}
> **來源**：[原文連結]({URL})
> **內容類型**：{文章 / 訪談 / 演講 / 影片 / 報告}
> **核心論點**：{一句話概括全文最重要的論點}
> **影音檔**：{若有下載影音檔，列出檔名；若無則省略此行}
> **字幕檔**：{若有產生 SRT 字幕檔，列出三個檔名：*.en.srt、*.zh-tw.srt、*.en&cht.srt；若無則省略此行}

---

## Key Takeaway（依重要性排序）

1. **{簡短標題}**
   {2-3 句深度說明：這個觀點為什麼重要？對讀者的啟發是什麼？}

2. **{簡短標題}**
   {說明}

---

## Key Quote（依易記性排序）

1. > "{原文引用}"
   >
   > — {講者/作者名稱}

   **中譯**：{繁體中文翻譯}
   **為何重要**：{一句話說明此引用的意義}

2. > "{原文引用}"
   ...

---

## Call to Action（依可操作性排序）

1. **{具體行動標題}**
   - **做什麼**：{明確的執行步驟}
   - **為什麼**：{預期效果或潛力}

---

## Best Practice（第一手經驗）

1. **{實踐標題}**
   {講者/作者的具體做法描述，包含背景脈絡}

---

## Unique Secret（與眾不同的洞見）

1. **{洞見標題}**
   - 🔸 主流觀點：{大部分人相信的 X}
   - 🔹 講者洞見：{但講者發現事實是 Y}
   - 💡 為何重要：{這個差異帶來的影響}

---

## Fun Story（有趣故事）

1. **{故事標題}**
   {故事內容簡述，保留趣味性}

---

## One Page Infograph Outline

### 📌 {主標題}
**{副標題：一句話核心訊息}**

**區塊 1：{主題}**
- {重點 1}
- {重點 2}

**區塊 2：{主題}**
- {重點 1}
- {重點 2}

**區塊 3：{主題}**
- {重點 1}
- {重點 2}

> 💬 金句："{最具代表性的一句話}"
```

---

## 折疊閱讀版

在完整筆記末尾，附加一個以 `<details>` 標籤包裝的折疊版本：

- 用 `---` 與正文分隔
- 標題：`## 📖 折疊閱讀版`
- 每個 section 各自一個 `<details>` 區塊
- `<summary>` 格式：`**Section 名稱**（N 條）`
- 折疊內容為該 section 的精簡版（每條一行摘要）

範例：

```markdown
---

## 📖 折疊閱讀版

<details>
<summary><b>Key Takeaway</b>（5 條）</summary>

1. **標題** — 一行摘要
2. **標題** — 一行摘要
...
</details>

<details>
<summary><b>Key Quote</b>（3 條）</summary>

1. "引用片段..." — 講者名稱
2. "引用片段..." — 講者名稱
...
</details>
```

---

## 輸出格式

請先輸出內容的背景摘要（作者、日期、核心論點），然後依序完成以下所有適用的輸出區塊：

---

### Output 1 → Key Takeaway ⭐ 必要區塊
- 從內容中，歸納出最多 10 個 Key Takeaway
- 依照「重要性」由高至低排序
- 每個 takeaway 需包含：
  - **簡短標題**（粗體）
  - **深度說明**（2-3 句）：不只是「作者說了什麼」，而是「為什麼這很重要」和「對讀者的啟發」
- 萃取層次要求：事實（作者說了什麼）→ 意義（為什麼這很重要）→ 啟發（讀者可以從中學到什麼）
- 若內容有與主流看法不同之處，在相關 takeaway 中點出差異

### Output 2 → Key Quote ⭐ 必要區塊
- 從內容中，抓出最多 10 個令人印象深刻、或值得記住的 Quote
- 依照「易記性」由高至低排序
- 每個 quote 需包含：
  - 原文引用（保留原語言，使用 blockquote 格式）
  - 講者/作者歸屬
  - 繁體中文翻譯（若原文非中文）
  - 一句話說明為何此引用重要
- 優先選擇：具體生動的表述 > 抽象概念性的陳述

### Output 3 → Call to Action 📋 條件區塊
- 從內容中，抓出最多 10 個可以具體操作執行的 Action，或是有潛力的投資創業機會
- 依照「可操作性、潛力性」由高至低排序
- 每個 action 需包含：
  - **具體行動標題**（粗體）
  - **做什麼**：明確的執行步驟，讀者看完就能動手
  - **為什麼**：預期效果或潛力說明
- **禁止**輸出「持續學習」「保持開放心態」等抽象建議

### Output 4 → Best Practice 📋 條件區塊
- 從內容中，抓出最多 10 個 Best Practice，或第一手親身經驗
- 重點聚焦在講者/作者的實際做法與實戰經驗
- 每個 practice 需包含：
  - **實踐標題**（粗體）
  - 具體做法描述，包含背景脈絡（在什麼情境下、怎麼做、效果如何）
- **禁止**輸出泛泛的「業界最佳實踐」，只收錄講者/作者親身驗證過的做法

### Output 5 → Unique Secret 📋 條件區塊
- 從內容中，抓出最多 10 個「有什麼跟其他多數人有不同看法，但講者卻覺得很重要的事實」
- 依照「與眾不同性」由高至低排序
- 嚴格格式：
  - 🔸 主流觀點：{大部分人相信的 X}
  - 🔹 講者洞見：{但講者發現事實是 Y}
  - 💡 為何重要：{這個差異帶來的影響}
- **禁止**把普通觀點包裝成「與眾不同」，必須是真正有反差的洞見

### Output 6 → Fun Story 📋 條件區塊
- 從內容中，抓出最多 10 個有趣、好玩、或奇特的小故事
- 依照「有趣性」由高至低排序
- 每個故事需是內容中明確提到的具體事件或軼事
- **禁止**把論點改寫成「故事」，必須是真正的敘事性內容

### Output 7 → One Page Infograph Outline ⭐ 必要區塊
- 綜合上述萃取的內容，找出知識主題的脈絡
- 輸出一頁 Infograph 圖表的文字大綱
- 結構要求：
  - 📌 主標題 + 副標題
  - 3-5 個內容區塊，每個區塊含標題和 2-3 個重點
  - 底部金句（選自 Key Quote 中最具代表性的一句）
- 適合後續轉製為視覺化圖表

---

## Gotchas

以下是常見的錯誤模式，務必避免：

### 引用歸屬錯誤
作者/講者在文章中引用他人的話時，不要把被引用者的觀點歸為作者本人的觀點。Key Quote 區塊中必須正確標註說話者。如果作者說「正如 Paul Graham 所言：...」，這是 Paul Graham 的話，不是作者的話。

### Key Takeaway 流於表面
Key Takeaway 不是段落摘要。每個 takeaway 必須回答「為什麼這很重要？」和「這改變了什麼？」。如果一個 takeaway 可以套用在任何類似主題的文章上，那就太泛了——需要更具體。

### 條件性區塊全數輸出
Call to Action、Best Practice、Unique Secret、Fun Story 是條件性區塊。不是每篇文章都有這四種內容。在輸出前先問自己：「原文中真的有明確的第一手實踐經驗嗎？」如果沒有，就不要硬生出 Best Practice 區塊。寧可少輸出，也不要捏造。

### 字幕擷取失敗未處理
影片/podcast 的字幕擷取可能因平台限制而失敗。如果 WebFetch 無法取得字幕，應改用可取得的文字內容（如文章描述、評論區摘要），並在筆記開頭註明「字幕無法擷取，以下基於可取得的文字內容」。不要因為字幕失敗就整個 skill 失敗。

## 語言

所有輸出使用繁體中文（zh-TW）。原文引用保留原語言，並附上繁體中文翻譯。

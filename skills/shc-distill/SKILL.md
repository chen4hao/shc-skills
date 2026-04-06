---
name: shc-distill
description: >
  萃取網路文章、訪談、演講、影片、podcast、電子書(PDF/epub) 的學習重點精華，整理成結構化 markdown 筆記並儲存。
  當來源為訪談影片或 podcast 時，會自動擷取完整字幕並存為三個 SRT 字幕檔：英文(*.en.srt)、繁體中文(*.zh-tw.srt)、中英雙語(*.en&cht.srt)。
  當來源為大型內容（如電子書 PDF/epub，超過 50 頁）時，自動分段處理並用子代理並行萃取各段，最後產出分段筆記與彙總筆記。
  當使用者提供 URL 或本地檔案路徑並要求萃取重點、整理筆記、提取學習精華、summarize key takeaways 時觸發。
  Use when user shares a URL or local file path and wants to extract insights, distill key takeaways,
  summarize learnings, or create study notes from articles, interviews, talks,
  videos, podcasts, essays, blog posts, or books (PDF/epub). When the source is an interview video
  or podcast, automatically extracts and saves three SRT subtitle files: English
  (*.en.srt), Traditional Chinese (*.zh-tw.srt), and bilingual (*.en&cht.srt).
  When the source is a large document (e.g., book PDF/epub over 50 pages), automatically
  segments content and processes each segment in parallel using subagents, producing
  per-segment notes and a consolidated summary.
---

# 學習萃取專家 | Distill

## 你的角色

* 你是一名學習專家，熟悉不同領域的專業，擅長掌握事物的本質重點，能引導新手輕易地理解各種主題概念並學習新知技能。
* 使用者是一個對各種事物、主題充滿好奇心的學習者，希望能夠透過網路影片、訪談、演講、文章來學習各種知識及技能。
* 為了能「更好、更有效地學習」各種知識技能，解決無知無能的焦慮。
* 核心學習方法：直接從各領域專家的第一手訪談、演講、文章等內容學習，並從中萃取出重點精華。

## 處理流程

1. **取得內容**：根據來源類型取得內容：
   - **網頁 URL**：使用 WebFetch 取得完整內容。若內容過長或需要更多細節，進行第二次 fetch 聚焦於引用語句、數據、故事等細節。
   - **本地 PDF/epub 檔案**（`file://` 路徑或絕對路徑）：使用 Read 工具讀取 PDF（每次最多 20 頁）。先讀取前 20 頁判斷全文結構（目錄、章節數、總頁數），再決定是否進入「大型內容分段處理」流程（見下方規則）。
   - **X/Twitter 平台 fallback**：若 URL 為 `x.com` 或 `twitter.com` 的貼文（格式如 `https://x.com/{user}/status/{id}`），因 X 平台封鎖爬取，WebFetch 通常會失敗（402 錯誤）。此時依序嘗試以下替代方案：
     1. **Twitter Thread Reader**（優先）：將 URL 轉換為 `https://twitter-thread.com/t/{status_id}`，例如 `https://x.com/bcherny/status/2007179832300581177` → `https://twitter-thread.com/t/2007179832300581177`
     2. **oEmbed API**：嘗試 `https://publish.twitter.com/oembed?url={原始URL}` 取得基本推文內容
     3. **WebSearch**：用作者名稱和推文關鍵字搜尋，從搜尋結果中拼湊內容
   - 若最終仍無法取得完整內容，在筆記開頭註明資料來源的限制。
2. **大型內容分段處理**（條件步驟）：若內容超過 50 頁（PDF/epub 書籍），進入分段處理流程（見下方「大型內容分段處理規則」）。此步驟會取代步驟 3-6，改為並行萃取各分段並產出彙總筆記。
3. **字幕擷取**（條件步驟）：若來源是影片或 podcast 的訪談/對話內容，執行字幕擷取流程（見下方「字幕擷取規則」）。**必須**產出三個 SRT 字幕檔：`.en.srt`（英文）、`.zh-tw.srt`（繁體中文）、`.en&cht.srt`（中英雙語）。完整流程：下載 → 去重 → 翻譯補全 → 合併 → 驗證。
4. **適用性評估**：通讀全文後，先判斷每個輸出區塊是否有足夠素材（見下方「區塊適用性判斷」）。
5. **深度萃取**：根據下方的輸出格式，對每個適用區塊進行深度分析並萃取內容精華。
6. **輸出結果**：依序輸出所有適用區塊，省略不適用的區塊。
7. **儲存檔案**：將完整輸出儲存為 markdown 檔案（見下方儲存規則）。若步驟 3 有產生 SRT 字幕檔，在輸出末尾附上字幕檔路徑。

## 大型內容分段處理規則

本步驟僅在來源為**大型文件（PDF/epub 書籍，超過 50 頁）**時執行。一般網頁文章、影片、podcast 跳過此步驟。

### 判斷邏輯

```
來源是否為本地 PDF/epub 檔案？
├─ 否 → 跳過，繼續正常流程
└─ 是 → 總頁數是否超過 50 頁？
    ├─ 否 → 跳過，當作一般文章處理
    └─ 是 → 進入分段處理流程
```

### 分段處理流程

#### 步驟 1：結構掃描與分段規劃

1. 用 Read 工具讀取前 20 頁，識別目錄、章節結構、總頁數
2. 規劃分段策略：按章節自然邊界切分，每段 30-60 頁為宜
3. 確定每段的頁碼範圍和章節主題

#### 步驟 2：並行讀取所有頁面

- 用 Read 工具並行讀取所有頁面（每次最多 20 頁，多個 Read 呼叫可並行）
- 讀取時為每個分段整理**內容摘要**（包含關鍵論點、引用、故事、案例等細節）
- **重要**：掃描版 PDF（圖片）只能由主 context 的 Read 工具讀取，子代理無法直接讀取 PDF。因此必須在主 context 中將 OCR 後的文字內容整理成充足的摘要，傳入子代理的 prompt

#### 步驟 3：啟動子代理並行萃取

- 使用 **Agent 工具**一次性啟動所有分段的子代理（在同一個訊息中發出多個 Agent 呼叫）
- 每個子代理負責一個分段的萃取
- 子代理設定：
  - `model: "sonnet"` — 使用 sonnet 模型節省成本
  - `mode: "bypassPermissions"` — 避免子代理卡在權限確認
  - `run_in_background: true` — 背景執行，並行處理
- 每個子代理的 prompt 必須包含：
  - 該分段的完整內容摘要（從步驟 2 整理的摘要）
  - 完整的輸出格式模板（Key Takeaway、Key Quote 等所有區塊）
  - 明確的輸出檔案路徑（含章節編號）
  - 區塊適用性判斷規則

**子代理 prompt 範本**：
```
你是學習萃取專家。請根據以下內容，為《{書名}》{章節名稱}（頁 X-Y）撰寫萃取筆記。
所有輸出使用繁體中文。

本章核心內容摘要：
{此處放入主 context 整理的詳細內容摘要}

請將筆記寫入檔案 {輸出路徑}

格式要求：
# {書名} — {章節名稱}
> **作者**：{作者}
> **來源**：《{書名}》{章節}（頁 X-Y）
> **內容類型**：書籍章節
> **核心論點**：{一句話}
---
## Key Takeaway（依重要性排序）
## Call to Action  ← 條件區塊
## Mistakes & Lessons Learned  ← 條件區塊
## Unique Secret  ← 條件區塊
## Best Practice  ← 條件區塊
## Fun Story  ← 條件區塊
## Key Quote（依易記性排序）
## One Page Infograph Outline
---
## 📖 折疊閱讀版

條件區塊素材不足就完全省略。原文引用保留原文語言。
```

#### 步驟 4：等待所有子代理完成

- 系統會自動通知子代理完成，**嚴禁輪詢**
- 在等待期間，可以處理不依賴子代理結果的工作（如整理彙總筆記的框架）

#### 步驟 5：產出彙總筆記

所有分段筆記完成後，在主 context 中：

1. 讀取所有分段筆記
2. 從各分段中再次篩選精華，按照同樣的輸出格式產出**彙總筆記**
3. 彙總筆記的特殊要求：
   - Key Takeaway、Key Quote 精選全書 Top 10（去重、按重要性重新排序）
   - 其他條件區塊（Call to Action、Mistakes、Unique Secret、Best Practice、Fun Story）也從全書範圍精選最佳內容
   - 在 metadata 區塊列出所有分段筆記的連結
   - One Page Infograph Outline 涵蓋全書脈絡

#### 步驟 6：儲存所有檔案

- 分段筆記命名：`{年份}-{月份}-{書名}-Ch{N}-{章節名稱}.md`
- 彙總筆記命名：`{年份}-{月份}-{書名}-彙總.md`
- 所有檔案存放在同一目錄下

### 注意事項

- **子代理的內容摘要必須充足**：子代理無法讀取 PDF，因此主 context 傳入的摘要必須包含所有關鍵論點、引用原文、具體數據、故事細節。摘要不足會導致子代理的萃取品質下降。
- **分段邊界對齊章節**：優先按書的章節自然邊界切分，避免在段落中間切斷。
- **保留分段筆記**：分段筆記是最終交付物的一部分，不要刪除。彙總筆記是額外的精華再萃取。
- **並行效率**：儘可能在同一個訊息中啟動所有子代理，最大化並行效率。

---

## 區塊適用性判斷

每個區塊在輸出前必須先評估內容是否有足夠素材支撐。區塊分為兩類：

**必要區塊**（所有內容類型都必須輸出）：
- Key Takeaway
- Key Quote
- One Page Infograph Outline

**條件區塊**（僅在內容中有明確相關素材時才輸出，以下為輸出順序）：
- Call to Action — 需有明確可操作的建議或機會
- Mistakes & Lessons Learned — 需有作者/講者明確承認的錯誤或失敗教訓
- Unique Secret — 需有與主流觀點明確不同的看法
- Best Practice — 需有講者/作者的第一手經驗或實際做法
- Fun Story — 需有具體的故事或軼事

**判斷規則**：
- 若條件區塊的素材不足（少於 2 個有品質的項目），則**完全省略該區塊**，不要輸出區塊標題
- **嚴禁硬擠**：不要為了湊數而把不相關或太勉強的內容塞進區塊
- 寧可少輸出一個區塊，也不要輸出低品質的內容

## 影音與字幕擷取規則

本步驟僅在來源為**影片（YouTube 等）或 podcast 的訪談/對話內容**時執行。純文字文章跳過此步驟。

**最終目標**：
1. 產出**三個 SRT 字幕檔**——這是**硬性要求**：
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

為避免權限系統和安全啟發式檢查阻擋，執行 Bash 指令時遵守以下規則：

**腳本目錄**：所有 Python 腳本已預先存在於 `/Users/chen4hao/Workspace/aiProjects/shc-skills/skills/shc-distill/scripts/`（以下簡稱 `$SCRIPTS`）。**不需要用 Write 工具建立腳本**，直接用 Bash 執行即可。

- **禁止 `python3 -c '...'`** 和 **heredoc**——會觸發安全啟發式警告。
- **禁止使用複合命令**（`&&`、`||`、`;`、`|`）——每個工具呼叫應獨立發出。
- **禁止使用 shell 重導向**（`2>&1`、`2>/dev/null`、`> file`）。
- **禁止使用 `cd`**——一律使用絕對路徑。
- **禁止使用 ffmpeg**——dedup.py 已能處理 VTT 和 SRT。
- **禁止使用 bash `grep`**——改用內建 Grep 工具。
- **可以**在同一訊息中平行發出多個獨立的 Bash 呼叫。
- **暫存目錄命名**：每次 distill 使用**唯一暫存目錄** `/tmp/distill-{VIDEO_ID}/`（例如 `/tmp/distill-xzQJWLWiYYE/`）。從 URL 提取影片 ID（YouTube 的 `v=` 參數值）。若無法提取，使用 URL 的 MD5 hash 前 8 位。**嚴禁使用固定的 `/tmp/distill-subs/`**——會被並行會話覆蓋。
- **暫存目錄讀取**：使用 Read 工具或 `cat`、`head`、`tail` 命令。子代理（`bypassPermissions` 模式）不受此限。

### 擷取流程

#### 步驟 A：下載字幕（優先）+ 條件性下載影音檔

**核心策略：字幕優先，影音按需。** 先嘗試只下載字幕和 metadata，若成功取得字幕檔則**跳過影音下載**。只有在完全無法取得任何字幕時，才下載完整影音檔（後續用 Whisper STT 產生字幕）。

不下載中文自動字幕（原因：步驟 C 一律從英文翻譯為中文，中文自動字幕不會被使用，且下載中文字幕常觸發 YouTube 429 限流導致整個下載中斷）。

用 Bash 執行下載（`$SCRIPTS` = `/Users/chen4hao/Workspace/aiProjects/shc-skills/skills/shc-distill/scripts`）：
```bash
uv run python3 $SCRIPTS/download.py "/tmp/distill-{VIDEO_ID}" "$URL"
```

下載完成後，用 Bash 檢查結果：
```bash
ls /tmp/distill-{VIDEO_ID}/
```

**判斷後續流程**：根據輸出中的 `SUBS_AVAILABLE` 判斷：
- `YES`：有字幕，繼續步驟 B（去重清理）。**無影音檔需要處理。**
- `NO`：無字幕但有影音檔，繼續步驟 B，並在步驟 B 之前/之後使用 Whisper STT 產生字幕。

> **VTT vs SRT**：`--convert-subs "srt"` 會自動將 VTT 轉為 SRT。若 yt-dlp 因中途錯誤而只產出 `.vtt` 檔，**不需要額外用 ffmpeg 轉檔**——步驟 B 的 dedup.py 已能直接處理 VTT 和 SRT 兩種格式。

#### 步驟 B：去重清理（必須執行）

YouTube 自動字幕使用漸進式顯示（progressive display），造成兩種重複：(1) 條目間重複——後面的條目包含前面的文字；(2) 條目內重複——同一條目的文字自身有重複片段。用 Python 腳本進行四階段清理：Phase 1 條目間去重、Phase 2 條目內去重、Phase 3 新文字提取、Phase 4 重新切割為自然語句字幕。同時解碼 HTML 實體（`&gt;` → `>`）並移除 `>>` 講者標記。

> **重要**：dedup.py **同時支援 VTT 和 SRT 輸入格式**，不需要事先用 ffmpeg 或其他工具轉檔。直接對 yt-dlp 下載的檔案執行即可。

用 Bash 執行去重腳本：
```bash
uv run python3 $SCRIPTS/dedup.py "/tmp/distill-{VIDEO_ID}"
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

**重要：子代理的檔案路徑規則**

子代理即使設定 `bypassPermissions` 也**無法存取 `/tmp/` 路徑**（不繼承父級權限）。因此：
- **子代理讀取的 SRT 檔案**必須位於**專案輸出目錄**（即最終儲存筆記的目錄）
- **子代理寫入的翻譯批次檔**也必須位於同一目錄
- 翻譯前，先將 `/tmp/distill-{VIDEO_ID}/` 中清理後的英文 SRT 複製到專案輸出目錄
- 翻譯完成後，合併腳本從專案輸出目錄讀取批次檔

**流程**：

1. 用 Bash 執行預拆腳本，**按條目數（非行數）**將英文 SRT 拆成多個獨立檔案，直接輸出到**專案輸出目錄**。**檔名必須包含 VIDEO_ID 前綴**以避免並行會話覆蓋：
```bash
uv run python3 $SCRIPTS/split_batches.py "/tmp/distill-{VIDEO_ID}/{英文clean檔名}" "{專案輸出目錄}" "{VIDEO_ID}"
```
   產出檔案命名為 `{VIDEO_ID}_en_batch_1.srt`、`{VIDEO_ID}_en_batch_2.srt` 等。
2. 用 **Agent 工具**一次性啟動所有批次的子代理（在同一個訊息中發出多個 Agent 呼叫），每個子代理：
   - `model: "sonnet"` — 使用 sonnet 模型節省成本
   - `mode: "bypassPermissions"` — 避免子代理卡在權限確認
   - `run_in_background: true` — 背景執行，並行處理
   - 任務：從**專案輸出目錄**讀取 `{VIDEO_ID}_en_batch_{X}.srt` **整個檔案**，翻譯為繁體中文，寫入 `{VIDEO_ID}_zh_batch_{X}.srt`

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

請用 Read 工具讀取 {專案輸出目錄}/{VIDEO_ID}_en_batch_{X}.srt **整個檔案**，
翻譯所有條目，然後用 Write 工具寫入 {專案輸出目錄}/{VIDEO_ID}_zh_batch_{X}.srt。

完成後，用 Grep 工具計算輸出檔的 `-->` 行數，確認與輸入條目數一致。回報兩個數字。
```

4. 等待**所有**子代理完成（系統會自動通知，**嚴禁輪詢** `ls` 檢查——啟動子代理後繼續撰寫萃取筆記等非依賴任務，或直接等待通知）
5. 用 Bash 執行合併腳本（注意：批次檔在**專案輸出目錄**，合併結果寫回 `/tmp/distill-{VIDEO_ID}/`）：
```bash
uv run python3 $SCRIPTS/combine_zh.py "{專案輸出目錄}" "/tmp/distill-{VIDEO_ID}" "{VIDEO_ID}"
```

> **驗證規則**：若 EN 和 ZH 條目數差距 > 5 條，需找出丟失最多條目的批次並重新翻譯該批次。差距 ≤ 5 條則由 merge.py 的時間戳對齊兜底。

**翻譯規則**（已寫入子代理 prompt 中）：
- 保留**完全相同的時間戳、序號和條目數量**（1:1 對應是雙語同步的關鍵）
- 翻譯時保持語句自然流暢，非逐字翻譯
- 參考前後文上下文翻譯，確保語意連貫
- 專有名詞（人名、公司名、技術名詞）保留原文
- 中文每行控制在 25 字以內

**嚴禁**：在主 context 中逐批翻譯。**嚴禁**跳過翻譯步驟。

#### 步驟 D：產出三個版本的 SRT 字幕檔

本步驟產出三個字幕檔：純英文、純中文、中英雙語。

用 Bash 執行合併腳本，產出三個版本的 SRT：
```bash
uv run python3 $SCRIPTS/merge.py "/tmp/distill-{VIDEO_ID}"
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

#### 步驟 E：複製字幕和影音檔到最終位置

**重要**：所有字幕檔的主檔名必須相同（例如主檔名為 `2026-03-Interview-with-Sam-Altman`，則產出 `.en.srt`、`.zh-tw.srt`、`.en&cht.srt`）。影音檔也使用相同主檔名，但存放在統一的影音目錄。

**重要**：因為雙語字幕的檔名含 `&`（`.en&cht.srt`），直接在 Bash 中使用 `cp` 會觸發安全啟發式警告。因此所有複製操作統一寫成 Python 腳本執行。

**影音檔存放規則**：所有影音檔統一存放在 `/Users/chen4hao/Workspace/aiProjects/infoAggr/download/`，不與筆記放在同一目錄。若步驟 A 未下載影音檔（因為成功取得字幕），則跳過影音複製。

用 Bash 執行複製腳本：
```bash
uv run python3 $SCRIPTS/copy_files.py "/tmp/distill-{VIDEO_ID}" "{儲存目錄}" "/Users/chen4hao/Workspace/aiProjects/infoAggr/download" "{檔案名稱前綴}"
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

產出**三個 SRT 字幕檔**，與 markdown 筆記存放在**相同目錄**下。**影音檔**（若有下載）統一存放在 `/Users/chen4hao/Workspace/aiProjects/infoAggr/download/`。

範例：
```
/Users/chen4hao/Workspace/aiProjects/infoAggr/Lex-Fridman/
├── 2026-03-Interview-with-Sam-Altman.md              ← 萃取筆記
├── 2026-03-Interview-with-Sam-Altman.en.srt          ← 英文字幕
├── 2026-03-Interview-with-Sam-Altman.zh-tw.srt       ← 繁體中文字幕
└── 2026-03-Interview-with-Sam-Altman.en&cht.srt      ← 中英雙語字幕（en 在上）

/Users/chen4hao/Workspace/aiProjects/infoAggr/download/
└── 2026-03-Interview-with-Sam-Altman.mp4             ← 影片檔（僅在無字幕時才下載）
```

> **檔案命名規則**：所有檔案共用相同主檔名，字幕副檔名分別為 `.en.srt`、`.zh-tw.srt`、`.en&cht.srt`。影音檔副檔名依實際格式而定（`.mp4` 為影片、`.m4a` 為音訊），統一放在 `download/` 目錄。
> **影音下載條件**：只有在步驟 A 無法取得任何字幕時，才會下載影音檔（供 Whisper STT 使用）。

### 失敗處理

**分級降級**（必須按順序嘗試，禁止直接跳到最低級）：

1. **目標**：三個 SRT 字幕檔（`.en.srt` + `.zh-tw.srt` + `.en&cht.srt`）。影音檔僅在無字幕時下載（存放於 `download/`）
2. **降級 1**：若中文翻譯在子代理處理中累積錯誤過多，仍然產出三個 SRT 檔並在輸出末尾註明翻譯品質問題
3. **降級 2**：若連英文字幕都下載失敗（yt-dlp 完全無法取得任何字幕），下載影音檔後用 Whisper STT 產生字幕
4. **降級 3**：若 Whisper STT 也失敗，在輸出末尾附上：`> 字幕擷取：未成功 — {原因}`
5. **不阻擋後續的萃取流程**，繼續進行適用性評估和深度萃取

**嚴禁**：因為中文字幕下載失敗就直接放棄雙語目標。必須走子代理翻譯補全流程。

### 清理暫存檔

**時序要求**：必須在**所有翻譯子代理確認完成**且**字幕檔已成功合併並複製到最終位置**之後才執行清理。

清理範圍：
1. `/tmp/distill-{VIDEO_ID}/` 整個暫存目錄
2. 專案輸出目錄中的暫存檔（僅限此 VIDEO_ID 的 `{VIDEO_ID}_en_batch_*.srt`、`{VIDEO_ID}_zh_batch_*.srt`）

用 Bash 執行清理腳本：
```bash
uv run python3 $SCRIPTS/cleanup.py "/tmp/distill-{VIDEO_ID}" "{專案輸出目錄}" "{VIDEO_ID}"
```

---

## 儲存規則

將完整的萃取結果儲存為 markdown 檔案，遵循以下慣例：

- **儲存位置**：`/Users/chen4hao/Workspace/aiProjects/infoAggr/{作者或來源名稱}/{檔案名稱}.md`
- **目錄命名**：以作者名稱或來源名稱建立資料夾（英文用連字號分隔，例如 `Matt-Shumer`；中文直接使用，例如 `簡立峰`）
- **檔案命名**：`{年份}-{月份}-{簡短標題}.md`，例如 `2026-02-Something-Big-is-Happening.md`
- 若資料夾不存在，先建立資料夾
- 檔案開頭包含 metadata 區塊

### Markdown 檔案結構範本

```markdown
# {文章/演講標題}

> **作者**：{作者全名} — {一句話背景介紹，如職稱或代表作}
> **發布日期**：{YYYY-MM-DD 或 YYYY-MM}
> **來源**：[原文連結]({URL})
> **內容類型**：{文章 / 訪談 / 演講 / 影片 / 報告}
> **核心論點**：{一句話概括全文最重要的論點}
> **影音檔**：{若有下載影音檔，列出完整路徑（位於 download/ 目錄）；若無則省略此行}
> **字幕檔**：{若有產生 SRT 字幕檔，列出三個檔名：*.en.srt、*.zh-tw.srt、*.en&cht.srt；若無則省略此行}

---

## Key Takeaway（依重要性排序）

1. **{簡短標題}**
   {2-3 句深度說明：這個觀點為什麼重要？對讀者的啟發是什麼？}

2. **{簡短標題}**
   {說明}

---

## Call to Action（依可操作性排序）

1. **{具體行動標題}**
   - **做什麼**：{明確的執行步驟}
   - **為什麼**：{預期效果或潛力}

---

## Mistakes & Lessons Learned（重大錯誤與教訓）

1. **{錯誤標題}**
   {錯誤的具體經過：在什麼情境下、做了什麼決定、造成什麼後果}
   **教訓**：{從這個錯誤中學到的具體原則或行為改變}

---

## Unique Secret（與眾不同的洞見）

1. **{洞見標題}**
   - 🔸 主流觀點：{大部分人相信的 X}
   - 🔹 講者洞見：{但講者發現事實是 Y}
   - 💡 為何重要：{這個差異帶來的影響}

---

## Best Practice（第一手經驗）

1. **{實踐標題}**
   {講者/作者的具體做法描述，包含背景脈絡}

---

## Fun Story（有趣故事）

1. **{故事標題}**
   {故事內容簡述，保留趣味性}

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
<summary><b>Call to Action</b>（N 條）</summary>

1. **行動標題** — 一行摘要
...
</details>

<details>
<summary><b>Mistakes & Lessons Learned</b>（N 條）</summary>

1. **錯誤標題** — 一行摘要 + 教訓
...
</details>

<details>
<summary><b>Unique Secret</b>（N 條）</summary>

1. **洞見標題** — 一行摘要
...
</details>

<details>
<summary><b>Best Practice</b>（N 條）</summary>

1. **實踐標題** — 一行摘要
...
</details>

<details>
<summary><b>Fun Story</b>（N 條）</summary>

1. **故事標題** — 一行摘要
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

### Output 2 → Call to Action 📋 條件區塊
- 從內容中，抓出最多 10 個可以具體操作執行的 Action，或是有潛力的投資創業機會
- 依照「可操作性、潛力性」由高至低排序
- 每個 action 需包含：
  - **具體行動標題**（粗體）
  - **做什麼**：明確的執行步驟，讀者看完就能動手
  - **為什麼**：預期效果或潛力說明
- **禁止**輸出「持續學習」「保持開放心態」等抽象建議

### Output 3 → Mistakes & Lessons Learned 📋 條件區塊
- 從內容中，抓出最多 10 個作者/講者明確承認的重大錯誤、失敗經驗或慘痛教訓
- 依照「教訓深度」由高至低排序
- 每個錯誤需包含：
  - **錯誤標題**（粗體）
  - **具體經過**：在什麼情境下、做了什麼決定、造成什麼後果
  - **教訓**：從這個錯誤中學到的具體原則或行為改變
- 必須是作者/講者**親身經歷**或**明確承認**的錯誤，不是泛泛的「應該避免的事」
- **禁止**把一般性建議改寫成「錯誤」，必須有真實的失敗故事或後果

### Output 4 → Unique Secret 📋 條件區塊
- 從內容中，抓出最多 10 個「有什麼跟其他多數人有不同看法，但講者卻覺得很重要的事實」
- 依照「與眾不同性」由高至低排序
- 嚴格格式：
  - 🔸 主流觀點：{大部分人相信的 X}
  - 🔹 講者洞見：{但講者發現事實是 Y}
  - 💡 為何重要：{這個差異帶來的影響}
- **禁止**把普通觀點包裝成「與眾不同」，必須是真正有反差的洞見

### Output 5 → Best Practice 📋 條件區塊
- 從內容中，抓出最多 10 個 Best Practice，或第一手親身經驗
- 重點聚焦在講者/作者的實際做法與實戰經驗
- 每個 practice 需包含：
  - **實踐標題**（粗體）
  - 具體做法描述，包含背景脈絡（在什麼情境下、怎麼做、效果如何）
- **禁止**輸出泛泛的「業界最佳實踐」，只收錄講者/作者親身驗證過的做法

### Output 6 → Fun Story 📋 條件區塊
- 從內容中，抓出最多 10 個有趣、好玩、或奇特的小故事
- 依照「有趣性」由高至低排序
- 每個故事需是內容中明確提到的具體事件或軼事
- **禁止**把論點改寫成「故事」，必須是真正的敘事性內容

### Output 7 → Key Quote ⭐ 必要區塊
- 從內容中，抓出最多 10 個令人印象深刻、或值得記住的 Quote
- 依照「易記性」由高至低排序
- 每個 quote 需包含：
  - 原文引用（保留原語言，使用 blockquote 格式）
  - 講者/作者歸屬
  - 繁體中文翻譯（若原文非中文）
  - 一句話說明為何此引用重要
- 優先選擇：具體生動的表述 > 抽象概念性的陳述

### Output 8 → One Page Infograph Outline ⭐ 必要區塊
- 綜合上述萃取的內容，找出知識主題的脈絡
- 輸出一頁 Infograph 圖表的文字大綱
- 結構要求：
  - 📌 主標題 + 副標題
  - 3-5 個內容區塊，每個區塊含標題和 2-3 個重點
  - 底部金句（選自 Key Quote 中最具代表性的一句）
- 適合後續轉製為視覺化圖表

## Gotchas

以下是常見的錯誤模式，務必避免：

### 引用歸屬錯誤
作者/講者在文章中引用他人的話時，不要把被引用者的觀點歸為作者本人的觀點。Key Quote 區塊中必須正確標註說話者。如果作者說「正如 Paul Graham 所言：...」，這是 Paul Graham 的話，不是作者的話。

### Key Takeaway 流於表面
Key Takeaway 不是段落摘要。每個 takeaway 必須回答「為什麼這很重要？」和「這改變了什麼？」。如果一個 takeaway 可以套用在任何類似主題的文章上，那就太泛了——需要更具體。

### 條件性區塊全數輸出
Call to Action、Best Practice、Unique Secret、Fun Story、Mistakes & Lessons Learned 是條件性區塊。不是每篇文章都有這五種內容。在輸出前先問自己：「原文中真的有明確的第一手實踐經驗嗎？」如果沒有，就不要硬生出 Best Practice 區塊。「原文中真的有作者親身承認的錯誤嗎？」如果沒有，就不要硬生出 Mistakes & Lessons Learned 區塊。寧可少輸出，也不要捏造。

### 字幕擷取失敗未處理
影片/podcast 的字幕擷取可能因平台限制而失敗。如果 WebFetch 無法取得字幕，應改用可取得的文字內容（如文章描述、評論區摘要），並在筆記開頭註明「字幕無法擷取，以下基於可取得的文字內容」。不要因為字幕失敗就整個流程失敗。

## 語言

所有輸出使用繁體中文（zh-TW）。原文引用保留原語言，並附上繁體中文翻譯。

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
   - **影片/podcast URL**（YouTube、Spotify 等）：**禁止 WebFetch**——YouTube 頁面只回傳 minified JS，WebFetch 無法取得任何有用資訊。直接跳到步驟 3 的字幕擷取流程，`download.py` 會同時輸出影片 metadata（Title、Channel、Upload date、Duration、Description），這是影片類來源的**唯一 metadata 來源**。
   - **網頁 URL**（非影片）：使用 WebFetch 取得完整內容。若內容過長或需要更多細節，進行第二次 fetch 聚焦於引用語句、數據、故事等細節。
   - **本地 PDF 檔案**（`file://` 路徑或絕對路徑）：使用 Read 工具讀取 PDF（每次最多 20 頁）。先讀取前 20 頁判斷全文結構（目錄、章節數、總頁數），再決定是否進入「大型內容分段處理」流程（見下方規則）。
   - **本地 epub 檔案**：epub 是 zip 壓縮包，**Read 工具會讀到亂碼**，必須使用預置腳本提取。先用 `--list` 掃描結構，再用 `--all` 提取所有章節為獨立 .txt 檔。**重要**：因為子代理無法存取 `/tmp/`，epub 必須直接提取到**專案輸出目錄下的 `_tmp_extract/` 子目錄**：
     ```bash
     uv run python3 $SCRIPTS/epub_extract.py "{epub路徑}" "{專案輸出目錄}/_tmp_extract" --list
     uv run python3 $SCRIPTS/epub_extract.py "{epub路徑}" "{專案輸出目錄}/_tmp_extract" --all
     ```
     提取後用 Read 工具讀取各 .txt 檔。**強烈建議先跑 `read_plan.py` 自動產生安全的 offset/limit 批次**（中文密度會自動降到 ~35 行）：`uv run python3 $SCRIPTS/read_plan.py {txt路徑} [--start N --end M]`，輸出可直接複製成 Read 呼叫。或讓子代理直接讀取。再根據章節數量決定是否進入「大型內容分段處理」流程。完成後清理 `_tmp_extract/` 目錄。
   - **X/Twitter 平台 fallback**：若 URL 為 `x.com` 或 `twitter.com` 的貼文（格式如 `https://x.com/{user}/status/{id}`），因 X 平台封鎖爬取，WebFetch 通常會失敗（402 錯誤）。此時依序嘗試以下替代方案：
     1. **Twitter Thread Reader**（優先）：將 URL 轉換為 `https://twitter-thread.com/t/{status_id}`，例如 `https://x.com/bcherny/status/2007179832300581177` → `https://twitter-thread.com/t/2007179832300581177`
        - **關鍵：不要用 WebFetch 讀這個站**。twitter-thread.com 把完整 thread 原文塞在 `<meta name="description">` 裡，但 WebFetch 的小模型對長內容會主動壓縮/改寫（實測會回傳條列摘要，並用 `[Full thread continues...]` 省略後半，即使 prompt 明確要求 verbatim 也無效）。正確作法：用 Bash 執行 `curl -sL "https://twitter-thread.com/t/{status_id}"`，再用 Read 工具讀取 persisted-output 檔，從 meta description 取得**無損的全文**。
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

**PDF 檔案**：
1. 用 Read 工具讀取前 20 頁，識別目錄、章節結構、總頁數
2. 規劃分段策略：按章節自然邊界切分，每段 30-60 頁為宜
3. 確定每段的頁碼範圍和章節主題

**epub 檔案**：
1. 用 `$SCRIPTS/epub_extract.py --list` 掃描結構，獲得章節清單和各章大小
2. 用 `$SCRIPTS/epub_extract.py --all` 提取所有章節為獨立 .txt 檔（存到 `{專案輸出目錄}/_tmp_extract/`，因為子代理無法存取 `/tmp/`）
3. 按章節自然邊界規劃分段（每段可包含 1-3 章，視大小而定）

#### 步驟 2：並行讀取所有頁面

**PDF 檔案**：
- 用 Read 工具並行讀取所有頁面（每次最多 20 頁，多個 Read 呼叫可並行）
- 讀取時為每個分段整理**內容摘要**（包含關鍵論點、引用、故事、案例等細節）
- **重要**：掃描版 PDF（圖片）只能由主 context 的 Read 工具讀取，子代理無法直接讀取 PDF。因此必須在主 context 中將 OCR 後的文字內容整理成充足的摘要，傳入子代理的 prompt

**epub 檔案**：
- 步驟 1 已將各章提取為獨立 .txt 檔，子代理可直接用 Read 工具讀取這些 .txt 檔
- 子代理 prompt 中提供 .txt 檔的完整路徑，讓子代理自行讀取並萃取
- **注意**：中文 .txt 檔讀取時 limit 設為 35 行（中文 token 密度是英文的 3-5 倍）

#### 步驟 3：啟動子代理並行萃取

**🔴 Checkpoint A — 分段大小門檻（啟動前必做）**

對每個規劃中的分段執行 `wc -l` 或目視檔案大小：
- **<200 行（中文）/ <15KB / <3 個短章**:**禁止派子代理**，主代理直接 Read + 撰寫筆記。理由：子代理啟動成本（context 轉移 + rate limit 風險）大於並行收益，而且小段內容回傳後若遇上下文壓縮極易丟失。
- **≥200 行**：可派子代理。

違反此規則的後果（實證）:Seg10 三章共 158 行，派子代理 → rate limit 失敗 → 內容遺失 → 主代理仍需自行讀檔重做，總耗時加倍。

- 使用 **Agent 工具**一次性啟動所有「夠大」的分段子代理（在同一個訊息中發出多個 Agent 呼叫）
- 每個子代理負責一個分段的萃取
- 子代理設定：
  - `model: "sonnet"` — 使用 sonnet 模型節省成本
  - `mode: "dontAsk"` — 避免子代理卡在權限確認（用於 Read 等工具）
  - `run_in_background: true` — 背景執行，並行處理
- **子代理不寫入檔案**：子代理的 Write 工具極不穩定（即使 `dontAsk` 也可能被 sandbox 拒絕），因此子代理只負責分析與回傳完整筆記內容，**由主代理統一用 Write 工具寫入所有分段筆記**。這避免子代理浪費時間在被拒的寫入嘗試上（每個節省 30-60 秒）。
- 每個子代理的 prompt 必須包含：
  - 該分段的完整內容摘要（從步驟 2 整理的摘要）
  - 完整的輸出格式模板（Key Takeaway、Key Quote 等所有區塊）
  - 區塊適用性判斷規則
  - **明確指示：不要嘗試寫入檔案，將完整筆記作為回傳結果輸出**

**🔴 共用模板檔案機制（防止 prompt 退化）**

手動為每個子代理重複寫完整模板，會從第 2-3 個開始自然退化（「格式同 Ch1」——但子代理看不到 Ch1）。因此**必須使用共用模板檔案**：

1. **啟動子代理前**，用 Write 工具將完整格式模板寫入專案輸出目錄的 `_distill_template.md`
2. **每個子代理 prompt** 只寫差異部分（書名、章節名、檔案路徑、作者資訊），格式部分改為：「用 Read 工具讀取 `{專案輸出目錄}/_distill_template.md` 獲得完整格式要求」
3. 彙總筆記完成後，`cleanup_epub_txt.py` 會一併清理此檔案（或手動刪除）

**共用模板檔案內容（`_distill_template.md`）**：
```markdown
# 書籍章節萃取格式模板

所有輸出必須使用繁體中文（zh-TW），包括任何開頭和結尾文字。原文引用保留原文語言。

直接以 `# ` 標題開頭，不要有任何前言文字（如「以下是筆記…」「所有章節已讀取…」）。結尾停在最後一個 `</details>` 標籤後，不要有任何後語（如「萃取完成，請主代理寫入…」）。

**重要：不要嘗試用 Write 工具或 Bash 寫入檔案（會被 sandbox 拒絕）。請將完整筆記內容直接作為你的回覆輸出，由主代理負責寫入。**

## H1 格式（assemble 依此辨識章節）

**H1 必須為固定格式**：`# Ch{N}: {Title}`（N=阿拉伯數字、Title=英文原章名，例如 `# Ch8: Greater Fools`、Prologue 用 `# Ch0: Prologue`）。第二行起再放完整書名/副標。禁止自由發揮。

## 完整格式結構

# Ch{N}: {章節英文原名}
## {書名} — {章節中文意譯}
> **作者**：{作者}
> **來源**：《{書名}》{章節}
> **內容類型**：書籍章節
> **核心論點**：{一句話概括本章最重要的論點}

---

## Key Takeaway（依重要性排序）
1. **{簡短標題}**
   {2-3 句深度說明：這個觀點為什麼重要？對讀者的啟發是什麼？}
（最多 10 個）

---

## Call to Action（依可操作性排序）← 條件區塊，素材不足完全省略
1. **{具體行動標題}**
   - **做什麼**：{明確的執行步驟}
   - **為什麼**：{預期效果或潛力}

---

## Mistakes & Lessons Learned ← 條件區塊，需有作者明確承認的錯誤或失敗教訓。素材不足完全省略
1. **{錯誤標題}**
   {錯誤的具體經過：在什麼情境下、做了什麼決定、造成什麼後果}
   **教訓**：{從這個錯誤中學到的具體原則或行為改變}

---

## Unique Secret ← 條件區塊，需有與主流觀點明確不同的看法。素材不足完全省略
1. **{洞見標題}**
   - 🔸 主流觀點：{大部分人相信的 X}
   - 🔹 講者洞見：{但講者發現事實是 Y}
   - 💡 為何重要：{這個差異帶來的影響}

---

## Best Practice ← 條件區塊，需有講者/作者的第一手經驗。素材不足完全省略
1. **{實踐標題}**
   {講者/作者的具體做法描述，包含背景脈絡}

---

## Fun Story ← 條件區塊，需有具體的故事或軼事。素材不足完全省略
1. **{故事標題}**
   {故事內容簡述，保留趣味性}

---

## Key Quote（依易記性排序）
1. > "{原文引用}"
   >
   > — {講者/作者名稱}

   **中譯**：{繁體中文翻譯}
   **為何重要**：{一句話說明此引用的意義}
（最多 10 個）

---

## One Page Infograph Outline

### 📌 {主標題}
**{副標題：一句話核心訊息}**

**區塊 1：{主題}**
- {重點 1}
- {重點 2}
（3-5 個區塊）

> 💬 金句："{最具代表性的一句話}"

---

## 📖 折疊閱讀版

<details>
<summary><b>Key Takeaway</b>（N 條）</summary>

1. **標題** — 一行摘要
...
</details>

（每個已輸出的 section 各一個 details 區塊，每條一行摘要）

## 區塊適用性規則
- 條件區塊（Call to Action、Mistakes、Unique Secret、Best Practice、Fun Story）素材不足（少於 2 個有品質的項目）就**完全省略**，不要輸出區塊標題
- **嚴禁硬擠**：不要為了湊數而把不相關的內容塞進區塊
- Mistakes 區塊：不只戲劇性失敗，「做了X才發現Y」也算合格素材
- 引用歸屬：作者引用他人的話不要歸為作者本人的觀點
```

**子代理 prompt 範本**（使用共用模板檔案時）：
```
你是學習萃取專家。請為《{書名}》{章節名稱}撰寫萃取筆記。

**步驟**：
1. 用 Read 工具讀取 `{專案輸出目錄}/_distill_template.md` 獲得完整格式要求
2. 用 Read 工具讀取 `{專案輸出目錄}/{txt檔名}` 整個檔案（不設 limit）
3. 根據格式模板和內容撰寫完整萃取筆記

書籍資訊（填入模板的變數）：
- 書名：{書名}
- 章節：Ch{N}: {英文章節名}
- 中文意譯：{章節中文意譯}
- 作者：{作者} — {一句話背景}

不要嘗試寫入檔案。將完整筆記直接作為回覆輸出。
```

#### 步驟 4：即時 Write + 累積彙總要點（嚴禁囤積）

- 系統會自動通知子代理完成，**嚴禁輪詢**
- 在等待期間，準備彙總筆記的框架（標題、章節列表、區塊模板）
- **每收到一個子代理結果，必須在「同一個訊息」中完成兩件事**：
  1. Write 該分章筆記到專案目錄
  2. 將該章的 Top Takeaway / Key Quote 摘要貼進主代理彙總草稿
- **嚴禁累積超過 2 個未寫入結果** — 一旦上下文壓縮，未寫入內容會永久丟失
- **🔴 Checkpoint B — 跨輪禁令**：子代理結果到手的「**同一輪訊息**」必須完成 Write，**禁止留到下一輪再寫**。即使該輪已經發了其他工具呼叫，也要把 Write 塞進同一批。一旦該輪結束而內容還在 context，視為高風險狀態（壓縮可能在任何輪次觸發）。
- **🔴 壓縮 summary 不可信**：若會話經歷過壓縮，summary 宣稱「某段內容仍在 context」一律不採信。下一步必須是「實際驗證磁碟檔案存在」或「重新從原始檔讀取」，禁止盲信。
- **拼裝多個任務時，優先用 `$SCRIPTS/assemble_book_notes.py`** 從 task .output 目錄一次性產出所有章節檔案，避免每次手寫解析腳本：
  ```bash
  uv run python3 $SCRIPTS/assemble_book_notes.py "{tasks_dir}" "{專案輸出目錄}" "{年份}-{月份}-{書名}"
  ```
  此腳本以 prompt 中的 `ch###_*.txt` 檔名作為章節對應的唯一可信來源，禁止從輸出 markdown 的 H1 反推章節順序。

#### 步驟 5：產出彙總筆記

所有分段筆記完成並寫入後，在主 context 中：

1. 讀取所有分段筆記（若子代理結果仍在 context 中，可直接使用）
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

- **子代理不寫入，主代理統一寫入**：子代理的 Write 工具極不穩定（即使 `mode: "dontAsk"` 也可能被 sandbox 拒絕，實測 6/6 全部失敗的情況屢見不鮮）。子代理只負責分析與回傳，所有檔案寫入由主代理執行。子代理 prompt 中必須明確說明「不要嘗試寫入檔案」。
- **epub 提取目標必須是專案輸出目錄**：子代理無法存取 /tmp/，因此 `epub_extract.py --all` 必須直接輸出到專案輸出目錄（如 `/Users/chen4hao/Workspace/aiProjects/infoAggr/{作者}/`）。**嚴禁先提取到 /tmp 再複製**——這會觸發 cp glob sandbox 警告和額外權限提示。
- **子代理的內容摘要必須充足**：子代理無法讀取 PDF，因此主 context 傳入的摘要必須包含所有關鍵論點、引用原文、具體數據、故事細節。摘要不足會導致子代理的萃取品質下降。對於 epub，子代理可直接讀取 .txt 檔，不需要在 prompt 中傳入摘要。
- **分段邊界對齊章節**：優先按書的章節自然邊界切分，避免在段落中間切斷。
- **保留分段筆記**：分段筆記是最終交付物的一部分，不要刪除。彙總筆記是額外的精華再萃取。
- **並行效率**：必須在同一個訊息中啟動**所有**子代理，不可分批。若 prompt 太長，優先減少子代理數量（增大每段覆蓋範圍），而非分批啟動。
- **🔴 Checkpoint C — Task list 二選一**：啟動子代理前決定一次:
  - **方案 A**：建立 Task list，且承諾「每收到一個子代理結果就 TaskUpdate」。
  - **方案 B**：完全不建 Task list，只靠子代理通知 + 本地檔案存在性驗證。
  - **禁止中間狀態**：建了 Task list 但全程不更新——過往實證每次都發生（包括本次 Bad Blood）。系統 reminder 會反覆提示，但維護成本若沒有事先承諾就不會被執行。寧可不建。

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

### Read 工具對 SRT 字幕檔的分塊規則

YouTube 自動字幕 clean 後常達 15-20k tokens，一次 Read 會爆 10k token 限制。**一律用 `offset + limit` 分塊讀取**：

- **英文 SRT**：每次 `limit=500` 行（每條字幕約 4 行，即約 125 條／次）
- **中文 SRT**：每次 `limit=300` 行（中文 token 密度是英文 3-5 倍）
- 30 分鐘訪談約 400 條字幕 → 英文 SRT 分 3 次讀取、中文分 5 次讀取
- 讀取主要用途是給主代理撰寫 distill 筆記時參考內容；翻譯本身由子代理處理，不需要主代理讀完整個檔案

### Write 工具的連續寫入注意事項

主代理接收多個子代理翻譯結果統一寫入時，**嚴禁在單一訊息中平行發出 ≥3 個 Write 呼叫**——注意力滑落會導致漏填 `content` 參數（已有慘痛前例）。正確做法：

- **每訊息最多 2 個 Write 平行呼叫**，下一訊息再發其餘
- 每次 Write 前，**目視確認 `content` 參數的字串長度非零**
- 子代理回傳若含 markdown 程式碼圍欄（` ``` `）或 HTML entity（`&gt;`），寫入前必須人工剝除，否則會污染 SRT 格式

### 擷取流程

#### 步驟 A：下載字幕（優先）+ 條件性下載影音檔

**核心策略：字幕優先，影音按需。** 先嘗試只下載字幕和 metadata，若成功取得字幕檔則**跳過影音下載**。只有在完全無法取得任何字幕時，才下載完整影音檔（後續用 Whisper STT 產生字幕）。

不下載中文自動字幕（原因：步驟 C 一律從英文翻譯為中文，中文自動字幕不會被使用，且下載中文字幕常觸發 YouTube 429 限流導致整個下載中斷）。

用 Bash 執行下載（`$SCRIPTS` = `/Users/chen4hao/Workspace/aiProjects/shc-skills/skills/shc-distill/scripts`）：
```bash
uv run python3 $SCRIPTS/download.py "/tmp/distill-{VIDEO_ID}" "$URL"
```

**判斷後續流程**：`download.py` 的 stdout 已包含所有判斷資訊（Title、Channel、Upload date、Duration、Description、`SUBS_AVAILABLE`），**不需要額外 `ls` 確認**。根據 `SUBS_AVAILABLE` 判斷：
- `YES`：有字幕，繼續步驟 B（去重清理）。**無影音檔需要處理。**
- `NO`：無字幕但有影音檔，**跳過步驟 B**，改用 `whisper_stt.py` 產生字幕：
```bash
uv run python3 $SCRIPTS/whisper_stt.py "/tmp/distill-{VIDEO_ID}/{VIDEO_ID}.mp4" "/tmp/distill-{VIDEO_ID}" --language {語言代碼}
```
  腳本會自動：(1) ffmpeg 偵測音量分佈，動態調整 hallucination-silence-threshold；(2) mlx_whisper 轉錄；(3) 中文影片自動用 OpenCC s2twp 簡轉繁，產出 `.zh-tw.clean.srt`。
  `--language` 常用值：`zh`（中文）、`en`（英文）。若不確定語言可省略，由 Whisper 自動偵測。
  **Whisper 產生的 SRT 不需要步驟 B 去重**（無漸進式顯示問題），直接跳到步驟 C。

> **VTT vs SRT**：`--convert-subs "srt"` 會自動將 VTT 轉為 SRT。若 yt-dlp 因中途錯誤而只產出 `.vtt` 檔，**不需要額外用 ffmpeg 轉檔**——步驟 B 的 dedup.py 已能直接處理 VTT 和 SRT 兩種格式。

#### 步驟 B：去重清理（僅 YouTube 自動字幕需要執行）

YouTube 自動字幕使用漸進式顯示（progressive display），造成兩種重複：(1) 條目間重複——後面的條目包含前面的文字；(2) 條目內重複——同一條目的文字自身有重複片段。用 Python 腳本進行四階段清理：Phase 1 條目間去重、Phase 2 條目內去重、Phase 3 新文字提取、Phase 4 重新切割為自然語句字幕。同時解碼 HTML 實體（`&gt;` → `>`）並移除 `>>` 講者標記。

> **重要**：dedup.py **同時支援 VTT 和 SRT 輸入格式**，不需要事先用 ffmpeg 或其他工具轉檔。直接對 yt-dlp 下載的檔案執行即可。

用 Bash 執行去重腳本：
```bash
uv run python3 $SCRIPTS/dedup.py "/tmp/distill-{VIDEO_ID}"
```

執行後，清理過的檔案存為 `*.clean.srt`。確認至少有一個英文 `.clean.srt` 檔。

#### 步驟 C：翻譯為雙語（子代理並行翻譯）

**核心策略：以原文字幕為主軌（master track），翻譯產生另一語言的字幕。**

YouTube 不同語言的自動字幕各自獨立分段，條目數量和時間切分都不同，直接合併必然導致中英文錯位。因此**一律使用清理後的原文字幕作為唯一來源**，透過翻譯產生對應的另一語言字幕。

| 已取得 | 翻譯方向 | `split_batches.py` LANG 參數 | `combine_zh.py` TARGET_LANG | `merge.py` --master |
|--------|----------|------|------|------|
| 英文 `.clean.srt` 存在 | EN → ZH（翻譯為中文） | `en`（預設） | `zh`（預設） | `en`（預設） |
| 僅中文 `.zh-tw.clean.srt` | ZH → EN（翻譯為英文） | `zh` | `en` | `zh` |
| 都沒有 | 標記失敗，繼續萃取流程 | — | — | — |

##### 子代理並行翻譯流程

字幕翻譯會嚴重污染主 context window，因此**必須委派給子代理**處理。使用 **sonnet 模型**以節省成本並加速。

**重要：子代理的檔案路徑規則**

子代理即使設定 `bypassPermissions` 也**無法存取 `/tmp/` 路徑**，且 **Write 工具極不穩定**（即使 `dontAsk` 也可能被 sandbox 拒絕）。因此翻譯子代理採用**回傳策略**：
- **子代理讀取的 SRT 檔案**必須位於**專案輸出目錄**（即最終儲存筆記的目錄）
- **子代理不寫入翻譯結果**，而是將完整翻譯後的 SRT 內容作為回傳結果輸出
- **主代理收到結果後**，用 `extract_translated_batches.py` 從 JSONL task output 一次性提取所有翻譯批次檔（自動 dedup + 驗證）
- 翻譯前，先將 `/tmp/distill-{VIDEO_ID}/` 中清理後的英文 SRT 複製到專案輸出目錄
- 翻譯完成後，提取腳本寫入批次檔，合併腳本從專案輸出目錄讀取批次檔

**流程**：

1. 用 Bash 執行預拆腳本，**按條目數（非行數）**將原文 SRT 拆成多個獨立檔案，直接輸出到**專案輸出目錄**。**檔名必須包含 VIDEO_ID 前綴**以避免並行會話覆蓋：
```bash
# EN→ZH 流程（英文原文，預設）：
uv run python3 $SCRIPTS/split_batches.py "/tmp/distill-{VIDEO_ID}/{英文clean檔名}" "{專案輸出目錄}" "{VIDEO_ID}"
# ZH→EN 流程（中文原文）：
uv run python3 $SCRIPTS/split_batches.py "/tmp/distill-{VIDEO_ID}/{中文clean檔名}" "{專案輸出目錄}" "{VIDEO_ID}" 8 zh
```
   腳本同時產出：
   - `{VIDEO_ID}_{LANG}_batch_{N}.srt` — 各批次 SRT 檔
   - `{VIDEO_ID}_prompt_batch_{N}.txt` — 各批次的完整子代理 prompt（含條目數、檔案路徑、翻譯規則、輸出格式，已自動依翻譯方向切換語言對）
   - `{VIDEO_ID}_agent_config.json` — Agent 啟動設定（含每個 batch 的 `agent_prompt` 和 `description`）
   - stdout 末尾會印出 phase-specific 提醒，告知「在同一個訊息中啟動全部 Agent」
2. **讀取 agent_config.json，一次性啟動所有 Agent**：
   - 用 Read 工具讀取 `{VIDEO_ID}_agent_config.json`
   - 對 `batches` 陣列中的每個 batch，發一個 Agent call：
     - `description`: batch 的 `description` 欄位
     - `prompt`: batch 的 `agent_prompt` 欄位（meta-prompt，指示子代理讀取對應的 prompt 檔案）
     - `model`: `agent_settings.model`（sonnet）
     - `mode`: `agent_settings.mode`（dontAsk）
     - `run_in_background`: `agent_settings.run_in_background`（true）
   - **所有 Agent call 必須在同一個回覆中發出**（腳本 stdout 已提醒）
   - 子代理收到 meta-prompt 後會自行 Read prompt 檔案，獲得完整翻譯指示
3. 等待**所有**子代理完成（系統會自動通知，**嚴禁輪詢** `ls` 檢查——啟動子代理後繼續撰寫萃取筆記等非依賴任務，或直接等待通知）
4. **從 JSONL task output 直接提取翻譯批次檔**（**禁止用 Write 工具逐一寫入**——浪費大量 context 且易轉錄出錯）。用 `extract_translated_batches.py` 一個指令完成提取 + 驗證 + 抽樣：
```bash
uv run python3 $SCRIPTS/extract_translated_batches.py "{tasks_dir}" "{專案輸出目錄}" "{VIDEO_ID}" "{TARGET_LANG}"
```
   - `{tasks_dir}`：從任一 task-notification 的 `<output-file>` 路徑取得父目錄
   - `{TARGET_LANG}`：EN→ZH 流程用 `zh`（預設），ZH→EN 流程用 `en`
   - 腳本自動：掃描所有 `.output` JSONL → 按 VIDEO_ID 過濾 → 識別批次/gap 編號 → 從**所有** assistant 訊息提取 SRT 條目（去重、清理 code fence）→ 合併 gap 條目 → 寫入批次檔 → 驗證條目數 → 抽樣顯示首尾
   - 走 `uv run` 路徑，**零權限確認**
6. 用 Bash 執行合併腳本（注意：批次檔在**專案輸出目錄**，合併結果寫回 `/tmp/distill-{VIDEO_ID}/`）：
```bash
# EN→ZH 流程（預設）：
uv run python3 $SCRIPTS/combine_zh.py "{專案輸出目錄}" "/tmp/distill-{VIDEO_ID}" "{VIDEO_ID}"
# ZH→EN 流程：
uv run python3 $SCRIPTS/combine_zh.py "{專案輸出目錄}" "/tmp/distill-{VIDEO_ID}" "{VIDEO_ID}" "en" "/tmp/distill-{VIDEO_ID}/{中文clean檔名}"
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
# EN→ZH 流程（預設，英文為主軌）：
uv run python3 $SCRIPTS/merge.py "/tmp/distill-{VIDEO_ID}"
# ZH→EN 流程（中文為主軌，保留所有原文條目）：
uv run python3 $SCRIPTS/merge.py "/tmp/distill-{VIDEO_ID}" --master zh
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
- 若資料夾不存在，用 `uv run python3 $SCRIPTS/ensure_dir.py "{目錄路徑}"` 建立（避免 `mkdir` 觸發權限提問）
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

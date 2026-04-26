---
description: "萃取網路文章、訪談、演講、影片、podcast、電子書(PDF/epub) 的學習重點精華，整理成結構化 markdown 筆記並儲存。當來源為訪談影片或 podcast 時，會自動擷取完整字幕並存為三個 SRT 字幕檔：英文(*.en.srt)、繁體中文(*.zh-tw.srt)、中英雙語(*.en&cht.srt)。當來源為大型內容（如電子書 PDF/epub，超過 50 頁）時，自動分段處理並用子代理並行萃取各段，最後產出分段筆記與彙總筆記。當使用者提供 URL 或本地檔案路徑並要求萃取重點、整理筆記、提取學習精華、summarize key takeaways 時觸發。Use when user shares a URL or local file path and wants to extract insights, distill key takeaways, summarize learnings, or create study notes from articles, interviews, talks, videos, podcasts, essays, blog posts, or books (PDF/epub). When the source is an interview video or podcast, automatically extracts and saves three SRT subtitle files: English (*.en.srt), Traditional Chinese (*.zh-tw.srt), and bilingual (*.en&cht.srt). When the source is a large document (e.g., book PDF/epub over 50 pages), automatically segments content and processes each segment in parallel using subagents, producing per-segment notes and a consolidated summary."
argument-hint: "[URL, local file path, or content source]"
---

# 學習萃取專家 | Distill

## 你的角色

* 你是一名學習專家，熟悉不同領域的專業，擅長掌握事物的本質重點，能引導新手輕易地理解各種主題概念並學習新知技能。
* 使用者是一個對各種事物、主題充滿好奇心的學習者，希望能夠透過網路影片、訪談、演講、文章來學習各種知識及技能。
* 為了能「更好、更有效地學習」各種知識技能，解決無知無能的焦慮。
* 核心學習方法：直接從各領域專家的第一手訪談、演講、文章等內容學習，並從中萃取出重點精華。

## 處理流程

0. **重複檢查**（Preflight）：在任何下載或處理之前，先確認此來源是否已被 distill 過。
   - **Grep pattern 選擇**：
     - 若檔名為 anna's archive / Library Genesis / Z-Library 等 **hash 格式**（如 `annas-arch-[hex].epub`、`libgen-[hex].epub`、純 md5/sha1 檔名，詳見 `feedback_anna_archive_preflight.md` 的 regex 清單）：URL/檔名 Grep 必 0 匹配，**改用書名 Grep**，並同訊息並行跑 `epub_extract.py --show-opf` 取得權威書名做 cross-check。
     - 其他情境沿用 URL/路徑 Grep：
       ```
       Grep pattern="{URL或檔案路徑，或書名}" path="/Users/chen4hao/Workspace/aiProjects/infoAggr" glob="*.md"
       ```
   - **若找到匹配**：讀取該 `.md` 檔所在目錄，確認 `.md` 和 `.srt` 檔案是否完整存在，並**判定屬於哪種情境**：
     - **(A) 全部存在 + 有彙總檔** → 告知使用者「此來源已處理過」，列出檔案路徑，**結束流程**
     - **(B) 分章 ≥10 個但無彙總檔**（常見於多次 distill 同書後）→ 進入「**重寫彙總**」特殊流程（見 `feedback_preflight_rewrite_summary_detection.md`）：
       - memory 組切換：只讀 4 個 workflow memory（`feedback_distill_book_workflow.md`、`feedback_distill_preflight_memory_check.md`、`feedback_distill_preflight_content_check.md`、`feedback_trust_tool_output.md`），**跳過** epub-extract 相關 4 個 memory（`epub_handling` / `epub_session_conflict` / `epub_opf_first_probe_later` / `epub_distill_efficiency`）——不會跑 `epub_extract.py` 提取流程
       - 選項列表**禁含「清理重做」類重做完整工作的選項**——既有分章是沉沒成本，重做純浪費且與使用者「補齊」意圖不符。合理選項只限：補彙總 / 清理半途殘片+補彙總 / 什麼都不做
       - Write 彙總前**不再 ls 或 Glob 檢查檔名衝突**——preflight Grep 已列出同目錄檔案清單，再跑 ls 違反 `feedback_trust_tool_output.md`
     - **(C) 部分檔案缺失但不屬於 (B)**（例如單一影片 distill 的 .srt 缺失） → 告知使用者哪些檔案缺失，詢問是否補全
   - **若無匹配** → 繼續步驟 1
   - **此步驟在 download.py 之前執行，零網路請求、零子代理啟動**

1. **取得內容**：根據來源類型取得內容：
   - **影片/podcast URL**（YouTube、Spotify、Apple Podcasts 等）：**禁止 WebFetch / WebSearch 先行找替代來源**——YouTube 頁面只回傳 minified JS；Apple Podcasts URL yt-dlp 原生支援（ApplePodcasts extractor，直接抓完整音訊 mp3）。直接跳到步驟 3 的字幕擷取流程，`download.py` 會同時輸出影片 metadata（Title、Channel、Upload date、Duration、Description），這是影片類來源的**唯一 metadata 來源**。**只有在 `download.py` 首次失敗後才走 WebSearch fallback**。
     - **Apple Podcasts 特別注意**：description 通常只列嘉賓（「ft. {嘉賓}」）而無主持人姓名，Whisper STT 對中文主持人姓名有系統性誤聽（2026-04-23 實例：「宋晏仁」被聽成「宋燕仁」）。**preflight 階段必須用 channel name 從 YouTube 或官方網站取得主持人姓名正字拼法**，不依賴 transcript。見 `feedback_podcast_host_name_verification.md`。
   - **網頁 URL**（非影片）：使用 WebFetch 取得完整內容。若內容過長或需要更多細節，進行第二次 fetch 聚焦於引用語句、數據、故事等細節。
   - **Auth-gated 學習平台 URL**（`learn.deeplearning.ai`、`coursera.org`、`udemy.com`、`edx.org` 等需登入才能看課程內容的平台）：**禁止先 WebFetch 再 fallback**——頁面在 auth wall 後，WebFetch 只拿到 marketing catalog，小模型會基於訓練集對「課程在講什麼」產生幻覺（2026-04-20 DL.AI 教訓：首次 advisor 因此誤判為「內容是幻覺」，使用者打斷兩次才走回正軌）。DL.AI 專用一鍵腳本：
     ```bash
     uv run --with browser-cookie3 --with requests --with beautifulsoup4 python3 \
       $SCRIPTS/fetch_dlai_course.py \
       --url "{課程 URL}" --email {Chrome 登入用 email} --out-dir /tmp/distill-{slug}
     ```
     腳本會自動：Chrome profile 匹配（查 `Local State.profile.info_cache.*.user_name`）→ 複製 Cookies DB 繞 WAL lock → 並行 fetch 所有 lesson → 從 `__NEXT_DATA__.props.pageProps.captions` 提取 transcript → 輸出 `all_transcripts.md`。細節見 `reference_chrome_profile_cookie_extraction.md` 與 `reference_dlai_course_structure.md`。其他平台（Coursera、Udemy 等）若流程相同，複製該腳本改 URL pattern 即可，核心 cookie 流程不變。
   - **本地 PDF 檔案**（`file://` 路徑或絕對路徑）：

     - **先判斷是文字型還是掃描版**：嘗試 `pdftotext -layout {pdf} /tmp/probe.txt && wc -c /tmp/probe.txt`——若輸出 >1KB 純文字，是文字型；輸出空或亂碼是掃描版。
     - **文字型 PDF（優先路徑）**：走 `pdf_book_prep.py` 一鍵 pipeline，**等同 epub 流程**（提取成 .txt 後派子代理讀）：
       ```bash
       uv run --with opencc-python-reimplemented python3 \
         $SCRIPTS/pdf_book_prep.py "{pdf路徑}" "{專案輸出目錄}/_tmp_{書名slug}_pdf" --isolate
       ```
       腳本自動：`pdftotext -layout` → OpenCC `s2twp`（簡→繁台灣正體）→ 按 `^\s*CHAPTER\s+(\d+)\s*$` 切分為 ch{NN}.txt → 嘗試 `mutool show outline` / `pdfinfo -listbookmark` 取 PDF 章名 bookmark。stdout 印 `EXTRACT_DIR=...`、`CHAPTER_COUNT=N`、`CHAPTERS=[(1, 'ch01.txt', kb), ...]`、`BOOKMARKS=true|false`。**子代理可直接讀 .txt 檔，避免主代理通讀 PDF 吃 context**。
     - **Content-verify（必做）**：PDF `/Title`、`/Author` 內建欄位不可信（掃描版常空白、下載站可改寫），檔名也沒驗證。**Read PDF pages=1-5**（封面 + 自序）找書名/封面/作者，與使用者提供的檔名或陳述比對；不符即停下告知使用者「檔名聲稱 X、封面顯示 Y」再繼續（同 epub content-verify 規則，見 `feedback_epub_session_conflict.md`）。**嚴禁**為了「掃描章節結構」通讀 PDF 超過 10 頁——該工作由 pdftotext + grep CHAPTER 完成，不需要主代理視覺確認（見 `feedback_pdf_distill_content_verify.md`）。
     - **章名抓取優先序**：(1) `mutool show <pdf> outline` 或 `pdfinfo -listbookmark`——中文 PDF 章節扉頁常為藝術字圖片，pdftotext 只能取到 `CHAPTER N` 英文標記，**bookmark 是中文章名的權威來源**；(2) 若 `BOOKMARKS=false`，再從各章首段內容推斷（各章首段通常描述主題，精度會稍降）。
     - **掃描版 PDF fallback**（pdftotext 空輸出）：只能用主代理 Read 工具讀取（每次最多 20 頁），手動整理摘要傳入子代理 prompt；但這是**高 context 成本路線**，盡量避免。
   - **本地 epub 檔案**：epub 是 zip 壓縮包，**Read 工具會讀到亂碼**，必須使用預置腳本提取。
     - **步驟 0（作者未知時必做）**：先用 `--show-opf` 一步讀 OPF metadata，取得作者/書名/出版日期/語言（權威來源，零網路請求、零子代理、無需 probe 章節）：
       ```bash
       uv run python3 $SCRIPTS/epub_extract.py "{epub路徑}" - --show-opf
       ```
       stdout 印 `CREATOR=...`、`TITLE=...`、`DATE=...`、`LANGUAGE=...`、`PUBLISHER=...`、`IDENTIFIER=...`。**嚴禁**建 `Author-TBD`/`_tmp_probe` 暫名目錄 probe 章節取作者——OPF 已提供權威資料。僅當 OPF 缺 `dc:creator`（輸出 `CREATOR=` 空）時才 fallback 走舊流程 probe Copyright 章。見 `feedback_epub_opf_first_probe_later.md`。
     - **步驟 1：結構掃描 + 提取**。用 `--list` 掃描結構，再用 `--all` 或 `--chapters N-M` 提取章節為獨立 .txt 檔。**重要**：因為子代理無法存取 `/tmp/`，epub 必須直接提取到**專案輸出目錄下的 `_tmp_extract_<hash>/` 子目錄**。**必加 `--isolate` flag**：腳本自動計算 epub 檔案 md5 前 8 位並在 output_dir 後綴，避免多 session 共享路徑互相覆寫（見 `feedback_epub_session_conflict.md`）：
       ```bash
       uv run python3 $SCRIPTS/epub_extract.py "{epub路徑}" "{專案輸出目錄}/_tmp_extract" --list
       uv run python3 $SCRIPTS/epub_extract.py "{epub路徑}" "{專案輸出目錄}/_tmp_extract" --all --isolate
       ```
     `--all --isolate` 的 stdout 第一行會印 `EXTRACT_DIR={實際路徑}`（例如 `…/_tmp_extract_a1b2c3d4`），**後續所有 Read、子代理 prompt 都用這個實際路徑**，不是 `_tmp_extract`。
     - **步驟 1.5（content-verify，必做）**：提取完成後，**用 Bash `sed -n '3p' {EXTRACT_DIR}/ch003*.txt` 取第 3 行書名**（不用 Read 工具——只讀 1 行用 sed 比 Read limit=5 更精確且零冗餘），與步驟 0 的 OPF `TITLE` 比對。若不符，**停下所有動作**告訴使用者「OPF 聲稱 X，章節內容顯示 Y，請確認真實書名」再繼續。OPF 可能被盜版/合集站台造假（anna's archive 等）——熟悉感不能跳過這步。**禁**Read 多行 +「順便收集前言素材」（見 `feedback_content_verify_scope_strict.md`）。**禁**對後置 untitled 章節（如 ch{N-3}~ch{N}）用 Bash head/Read 確認內容類型——從 `--list` 章名 + 大小 pattern 直接判斷：small + untitled 跳過；large(>5KB) + untitled + 連續 3+ 個出現在尾部 = 高機率為各章 epigraph 集合，可從 distill 範圍排除（見 `feedback_epub_distill_efficiency.md`）。
     - **Read transient 失敗 fallback**：若提取後對任一 .txt Read 持續失敗（≥2 次失敗、Bash 同檔可讀），是 notification 時序 transient（見 `feedback_read_transient_no_retry.md`）。**禁**重試 ≥3 次。Fallback：(1) 短章內容若已被其他章子代理引用，跳過該章 + 在彙總引用其他章；(2) 改用 Bash `sed -n '1,30p'` 一次性讀；(3) 派小子代理專讀該章。
     提取後用 Read 工具讀取各 .txt 檔。**強烈建議先跑 `read_plan.py` 自動產生安全的 offset/limit 批次**（中文密度會自動降到 ~35 行）：`uv run python3 $SCRIPTS/read_plan.py {txt路徑} [--start N --end M]`，輸出可直接複製成 Read 呼叫。或讓子代理直接讀取。再根據章節數量決定是否進入「大型內容分段處理」流程。完成後由 `cleanup_epub_txt.py` 清理所有 `_tmp_extract*/` 目錄。
   - **X/Twitter 平台 fallback**：若 URL 為 `x.com` 或 `twitter.com` 的貼文（格式如 `https://x.com/{user}/status/{id}`），因 X 平台封鎖爬取，WebFetch 通常會失敗（402 錯誤）。此時依序嘗試以下替代方案：
     1. **Twitter Thread Reader**（優先）：用 `fetch_x_thread.py` 一個指令完成抓取 + 解析 + HTML entity 解碼，直接輸出純文字到 stdout（或 `--out` 指定檔）：
        ```bash
        uv run python3 $SCRIPTS/fetch_x_thread.py {status_id_或完整URL}
        ```
        - 腳本內部：curl `twitter-thread.com/t/{status_id}` → regex 抓 `<meta name="description">` → `html.unescape` → 輸出
        - **禁止 WebFetch 讀 twitter-thread.com**：小模型對長 meta description 會主動摘要/截斷（`[Full thread continues...]`），即使 prompt 要求 verbatim 也無效
        - **禁止在主 context 手動串 curl + Grep + wc + Read 驗證**：這是熟悉感確認，和腳本功能重複——直接跑腳本讀 stdout 即可
     2. **oEmbed API**：嘗試 `https://publish.twitter.com/oembed?url={原始URL}` 取得基本推文內容
     3. **WebSearch**：用作者名稱和推文關鍵字搜尋，從搜尋結果中拼湊內容
   - 若最終仍無法取得完整內容，在筆記開頭註明資料來源的限制。
2. **大型內容分段處理**（條件步驟）：若內容超過 50 頁（PDF/epub 書籍），進入分段處理流程（見下方「大型內容分段處理規則」）。此步驟會取代步驟 3-6，改為並行萃取各分段並產出彙總筆記。
3. **字幕擷取**（條件步驟）：若來源是影片或 podcast 的訪談/對話內容，執行字幕擷取流程（見下方「字幕擷取規則」）。**預設**產出三個 SRT 字幕檔：`.en.srt`（英文）、`.zh-tw.srt`（繁體中文）、`.en&cht.srt`（中英雙語）。完整流程：下載 → 去重 → 翻譯補全 → 合併 → 驗證。**例外：純中文來源**（Bilibili 等中國平台、或 Whisper 偵測為 `zh`）**預設只產 `.zh-tw.srt` 單檔**，跳過 ZH→EN 翻譯 pipeline（見下方「影音與字幕擷取規則 → 純中文來源特例」）。**例外：多 P playlist**（如 Bilibili anthology >3 P）走「多 P 分段流程」，每個分 P 獨立處理（見下方「多 P playlist 特例」）。
4. **適用性評估**（必做自我評估，不可省略）：通讀全文後，在進入 advisor call 之前，**先在 context 中明確列出**每個條件區塊（Call to Action / Mistakes & Lessons Learned / Unique Secret / Best Practice / Fun Story）的候選素材與計數。規則：
   - 每個條件區塊的候選素材 **<2 項** → 預設省略該區塊（寫筆記時不輸出區塊標題）
   - 候選素材 ≥2 項但品質勉強 → 列出後讓 advisor 覆核
   - **嚴禁把普通論點/資料點硬塞進 Fun Story（須有敘事性軼事）或 Mistakes（須有作者第一人稱承認的失敗）**
   - **Mistakes 語言門檻（硬規則，不外包給 advisor）**：每項 Mistakes 候選都要通過「第一人稱失敗語言」檢查——原文必須含講者本人語氣的 `I tried`、`I was`、`my mistake`、`I didn't realize`、`I spent X doing Y before I...`、`what I got wrong` 之類表達。若原文是「AI 預設會 X」「業界常見 Y」「很多人都 Z」這類泛指敘述，歸到 Unique Secret 或 Key Takeaway，**不歸 Mistakes**。Phase 4 自我評估時套用此門檻，不要交給 advisor 把關——2026-04-25 Matt Pocock distill 教訓：「AI 預設水平切片」初版被誤歸 Mistakes，advisor 指出後才改。
   - **素材 traceability**：同一素材禁同時列入多個區塊候選；若已決定用於 Key Takeaway #N，標註「已用於 KT #N」，其他區塊不得重複登記（否則 advisor 幾乎必定指出重複，浪費 round-trip）。違規症狀：講者實例/故事同時出現在 KT 描述和 Fun Story 候選
   - **Best Practice 特別注意**：必須滿足「何時、怎麼做、效果如何」三要素，且是作者親身驗證過的可操作做法。全片開場 hook / framing premise 不算 Best Practice（見 `feedback_distill_framing_vs_practice.md`）
   - **CTA 具體值 trace**：CTA「做什麼」欄位的數字/時間/頻率必須在原文中逐字對應。原文只說「盡快」就寫「盡快」，禁自行補「48 小時內」「每週」等具體值（見 `feedback_cta_no_fabricated_specifics.md`）
   - 列出候選素材的輸出格式：每區塊一行，例如：`Fun Story 候選：1) 作者 Q&A 問「誰在用 FastMCP？」後自嘲（13:42）——故事性弱，資料點更多 | 2) React 下載量對照（03:00）——非敘事，屬資料 → 0 項合格素材 → 省略`
   - 此步驟的目的是讓自己先做硬門檻判斷，而非把判斷外包給 advisor 兜底
5. **深度萃取**：根據下方的輸出格式，對每個適用區塊進行深度分析並萃取內容精華。
6. **輸出結果**：依序輸出所有適用區塊，省略不適用的區塊。
7. **Write 前 call advisor**（必要）：在用 Write 工具寫入最終 markdown 筆記**之前**，call `advisor()` 一次。**最佳時機**是「原文通讀完、骨架 Write 完、條件區塊候選素材計數已在 context 中列出後」——此時 advisor 能對條件區塊取捨、作者 bio 表述、核心論點措辭給出最大價值的建議。**不要拖到 finalize 全部完成後才 call**（見 `feedback_distill_advisor_timing.md`）。理由：Write 是 substantive work（不可逆的交付物生成），advisor 會檢查結構完整性、metadata 正確性、條件區塊的適用性判斷是否合理。補單章/重寫彙總也適用（見 `feedback_distill_preflight_content_check.md`）。advisor 無參數，自動轉發完整 context。
8. **儲存檔案**：將完整輸出儲存為 markdown 檔案（見下方儲存規則）。若步驟 3 有產生 SRT 字幕檔，在輸出末尾附上字幕檔路徑。

## 大型內容分段處理規則

本步驟在來源為**大型內容**時執行。一般網頁文章、短影片跳過此步驟。

### 判斷邏輯

凡符合任一條件即進入分段處理流程：

```
是否屬於以下任一種類？
├─ 本地 PDF/epub 書籍，且總頁數 > 50 頁                → 進入
├─ 多 P playlist 影片，且 P 數 > 3                       → 進入（每個 P 一段）
├─ 單一長訪談/演講，且 STT 後原文總行數 > 2000 行          → 進入（按時間切 30-60 分鐘/段）
├─ 單一長文章/文件，且總字元 > 60000 字                  → 進入
└─ 以上皆非                                               → 跳過，走一般流程
```

**核心原則**：任何單次丟進主 context 會超過 ~30K tokens 原文的來源都該走分段流程——主代理只做 assembly 與跨段精選，不吞原文。2026-04-11 樊登 11 本書 distill 教訓：把 3157 行中文 TXT 全讀進主 context 是反模式，應派子代理分章處理。

### 分段處理流程

**🔴 主代理開工第一輪必須先宣告**（降低 system-reminder TaskCreate 干擾，見 `feedback_pdf_distill_content_verify.md` 第 5 點）

主代理在啟動子代理前的第一輪回覆中，在 text 中**逐字寫出**：

> 「本任務選**方案 B**：不建 Task list，靠子代理通知 + 磁碟檔案驗證追蹤進度。TaskCreate system-reminder 會忽略。」

後續 5-10 次 TaskCreate reminder 都不需要再重新判斷忽略，降低注意力負擔。適用場景：書籍 distill ≥ 10 子代理且預計單輪完成（見 `feedback_distill_book_workflow.md` 的 Checkpoint C）。

#### 步驟 1：結構掃描與分段規劃

**PDF 檔案（文字型，優先路徑）**：
1. 跑 `$SCRIPTS/pdf_book_prep.py {pdf} {專案輸出目錄}/_tmp_{slug}_pdf --isolate` 一鍵完成 pdftotext + s2twp + split。stdout 的 `EXTRACT_DIR=...` 為後續路徑。
2. Read `EXTRACT_DIR/outline.txt`（若 `BOOKMARKS=true`）取章名；否則從各章首段推斷。
3. 按 stdout 的 `CHAPTERS=[(n, filename, size_kb), ...]` 規劃分段：每章一個子代理（<15KB 主代理自讀、≥15KB 派子代理）。
4. 章節分布通常已由書本結構自然切好，一般不需要再合併或分割。

**PDF 檔案（掃描版 fallback）**：
1. 用 Read 工具讀取前 20 頁，識別目錄、章節結構、總頁數
2. 規劃分段策略：按章節自然邊界切分，每段 30-60 頁為宜
3. 主代理讀完所有頁面後整理摘要傳入子代理 prompt（因掃描版子代理無法讀）

**epub 檔案**：
1. 用 `$SCRIPTS/epub_extract.py --list` 掃描結構，獲得章節清單和各章大小
2. 用 `$SCRIPTS/epub_extract.py ... --all --isolate` 提取所有章節為獨立 .txt 檔（存到 `{專案輸出目錄}/_tmp_extract_<hash>/`，因為子代理無法存取 `/tmp/`；`--isolate` 強制加 epub hash 後綴防 session 衝突，stdout 印 `EXTRACT_DIR=<實際路徑>`，後續統一用此路徑）
3. **Content-verify**：用 Bash `sed -n '3p' {EXTRACT_DIR}/ch003*.txt` 取第 3 行書名（**不用 Read 工具**），對照步驟 0 的 OPF `TITLE`——不符即停（見 `feedback_epub_session_conflict.md` 與 `feedback_content_verify_scope_strict.md`）
4. 按章節自然邊界規劃分段（每段可包含 1-3 章，視大小而定）

#### 步驟 2：並行讀取所有頁面

**PDF 檔案（文字型，優先路徑）**：
- 步驟 1 已將各章提取為獨立 .txt 檔（並轉為繁體台灣正體），子代理可直接用 Read 工具讀取這些 .txt 檔
- 子代理 prompt 中提供 .txt 檔的完整路徑（如 `{EXTRACT_DIR}/ch01.txt`），讓子代理自行讀取並萃取
- **注意**：中文 .txt 檔讀取時 limit 設為 35-80 行（視 wrap 長度）——可跑 `read_plan.py` 產生安全 offset/limit 批次
- **與 epub 幾乎相同**：差別只在檔名格式（epub 是 `ch001__自序.txt` 這類；pdf_book_prep 輸出是 `ch01.txt` ~ `chNN.txt`）

**PDF 檔案（掃描版 fallback）**：
- 用 Read 工具並行讀取所有頁面（每次最多 20 頁，多個 Read 呼叫可並行）
- 讀取時為每個分段整理**內容摘要**（包含關鍵論點、引用、故事、案例等細節）
- **重要**：掃描版 PDF（圖片）只能由主 context 的 Read 工具讀取，子代理無法直接讀取 PDF。因此必須在主 context 中將 OCR 後的文字內容整理成充足的摘要，傳入子代理的 prompt。**這是 context 消耗最大的路線，盡量用 OCR 工具先轉為文字型 PDF 再走優先路徑**

**epub 檔案**：
- 步驟 1 已將各章提取為獨立 .txt 檔，子代理可直接用 Read 工具讀取這些 .txt 檔
- 子代理 prompt 中提供 .txt 檔的完整路徑，讓子代理自行讀取並萃取
- **注意**：中文 .txt 檔讀取時 limit 設為 35 行（中文 token 密度是英文的 3-5 倍）

#### 訊息順序樣板（書籍 distill ≥10 子代理）

書籍 distill 的工具呼叫應壓縮在 4-5 個訊息內，每訊息並行最大化：

**訊息 1（preflight，全並行）**：
- `epub_extract.py --show-opf`
- Grep 書名 `path=infoAggr glob="*.md"`
- `ls infoAggr | grep -i {作者}` 或 `Glob "*{作者}*"`（**禁 ls\|head**，見 `feedback_chinese_author_dir_check.md`）
- Read 6-8 個書籍 distill memory（`distill_book_workflow` / `epub_handling` / `epub_session_conflict` / `epub_opf_first_probe_later` / `epub_distill_efficiency` / `trust_tool_output` / `redistill_existing_book` / `read_transient_no_retry`）
- 若使用者要求保留舊彙總：再加 1 個 Read 既有彙總前 5 行確認結構

**訊息 2（提取 + content-verify）**：
- `mv {既有檔}.md {既有檔}-v1-backup.md`（若需保留舊彙總，見 `feedback_redistill_existing_book.md`）
- `epub_extract.py --all --isolate [--skip-tail-epigraphs]`（mv 與 epub_extract 並行；`--skip-tail-epigraphs` 自動跳過尾部連續 untitled 章節，常為各章 epigraph 集合）
- 等 stdout 印 `EXTRACT_DIR=...`，下一輪用 `sed -n '3p' {EXTRACT_DIR}/ch003*.txt` content-verify（不用 Read）

**訊息 3（啟動子代理 + template + skeleton + advisor，全並行）**：
- N 個 Agent calls（一次性，禁分批）
- Write `_distill_template.md` 到 EXTRACT_DIR
- Write 彙總骨架（佔位符版）到專案目錄
- `advisor()` 同訊息並行
- **送出前 hard checklist 對照**：在回覆 text 末逐字寫
  ```
  hard checklist: N Agent + 2 Write + 1 advisor + 0 Read = X tools
  實際組裝:      N Agent + 2 Write + 1 advisor + 0 Read = X tools
  ✅ match → send
  ```
  差一項禁送（見 `feedback_book_distill_advisor_recidivism.md`，已累犯 2 次）

**訊息 4-N+3（等待期）**：
- >12 子代理：每收到 completion 用 Edit 在彙總骨架對應位置回填 Top 1-3 takeaway + Top 1 quote
- ≤12 子代理：跳過骨架填充，全收齊後直接 Write

**訊息 N+4（收尾，全並行）**：
- `assemble_book_notes.py --use-h1`（產出分章 .md）
- Write 最終彙總（覆寫骨架，含跨章精選 Top 10 KT/CTA/US/BP/FS/KQ）
- `cleanup_epub_txt.py`（清 `_tmp_extract*` 含舊殘留）

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

1. **啟動子代理前**，用 Write 工具將完整格式模板寫入 **`{EXTRACT_DIR}/_distill_template.md`**（即 `_tmp_extract_<hash>/` 內部），**不是**寫到 `{專案輸出目錄}/_distill_template.md`。理由：模板放 EXTRACT_DIR 天然獲得 session 隔離，避免多 session 同作者同時跑時模板互相覆寫（見 `feedback_epub_session_conflict.md` 規則 4）。
2. **每個子代理 prompt** 只寫差異部分（書名、章節名、檔案路徑、作者資訊），格式部分改為：「用 Read 工具讀取 `{EXTRACT_DIR}/_distill_template.md` 獲得完整格式要求」
3. 彙總筆記完成後，`cleanup_epub_txt.py` 會連同整個 `_tmp_extract_<hash>/` 一併清理，不需額外處理

**共用模板檔案內容（`_distill_template.md`）**：
```markdown
# 書籍章節萃取格式模板

所有輸出必須使用繁體中文（zh-TW），包括任何開頭和結尾文字。原文引用保留原文語言。

直接以 `# ` 標題開頭，不要有任何前言文字（如「以下是筆記…」「所有章節已讀取…」）。結尾停在最後一個 `</details>` 標籤後，不要有任何後語（如「萃取完成，請主代理寫入…」）。

**重要：不要嘗試用 Write 工具或 Bash 寫入檔案（會被 sandbox 拒絕）。請將完整筆記內容直接作為你的回覆輸出，由主代理負責寫入。**

**重要：子代理不能呼叫 advisor()。禁止在輸出中寫「advisor 確認方向無誤」「與 advisor 討論後…」「advisor 指出…」等虛構對話片語——只有主代理能 call advisor，子代理撰寫筆記時沒有 advisor 參與。若需要描述流程，用中性描述（如「依模板格式撰寫」「根據章節內容萃取」）而非虛構 advisor 互動。**

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

## One Page Infograph Outline

### 📌 {主標題}
**{副標題：一句話核心訊息}**

**區塊 1：{主題}**
- {重點 1}
- {重點 2}
（3-5 個區塊）

> 💬 金句："{最具代表性的一句話}"

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
- **自檢 gate（必做）**：每寫完一個條件區塊**立刻**算候選素材項數；若 <2，現場刪除該區塊（**連同折疊閱讀版對應 details 段一起刪**）再繼續下一區塊。不要寫完所有區塊才事後檢查——主代理事後 Edit 是最後手段，不是預設流程
```

**子代理 prompt 範本**（使用共用模板檔案時）：
```
你是學習萃取專家。請為《{書名}》{章節名稱}撰寫萃取筆記。

**步驟**：
1. 用 Read 工具讀取 `{EXTRACT_DIR}/_distill_template.md` 獲得完整格式要求（EXTRACT_DIR 形如 `_tmp_extract_<hash>/`，由主代理從 `epub_extract.py --isolate` stdout 的 `EXTRACT_DIR=` 行取得）
2. 用 Read 工具讀取 `{EXTRACT_DIR}/{txt檔名}` 整個檔案（不設 limit）
3. 根據格式模板和內容撰寫完整萃取筆記

書籍資訊（填入模板的變數）：
- 書名：{書名}
- 章節：Ch{N}: {英文章節名}
- 中文意譯：{章節中文意譯}
- 作者：{作者} — {一句話背景}

不要嘗試寫入檔案。將完整筆記直接作為回覆輸出。
```

#### 步驟 4：收集結果 + 累積彙總要點

- 系統會自動通知子代理完成，**嚴禁輪詢**
- **🔴 壓縮 summary 不可信**：若會話經歷過壓縮，summary 宣稱「某段內容仍在 context」一律不採信。下一步必須是「實際驗證磁碟檔案存在」或「重新從原始檔讀取」，禁止盲信。

**分章筆記寫入：統一用 `assemble_book_notes.py`，嚴禁手動 Write**

task .output 已是持久化儲存（JSONL 檔在磁碟上），`assemble_book_notes.py` 會統一從所有 task output 提取並寫入分章筆記。手動 Write 單章 = 浪費 ~15KB context + 1 個工具呼叫，且後續被 assemble 覆寫。

- ⛔ **Checkpoint B「同輪必寫」規則在有 assemble 腳本時不適用**
- ⛔ 收到子代理通知時的第一反應必須是「等 assemble」而非「立刻 Write」
- ✅ 所有子代理完成後，一次性執行 assemble：
  ```bash
  uv run python3 $SCRIPTS/assemble_book_notes.py "{tasks_dir}" "{專案輸出目錄}" "{年份}-{月份}-{書名}" --use-h1
  ```
  **必須加 `--use-h1`**：從子代理輸出的 H1 `# Ch{N}: {Title}` 讀取正確章節號和標題。不加此旗標時，腳本用 epub txt 檔序號（ch005=0），幾乎所有書都會產生章節編號偏移。
- `assemble_book_notes.py` 內建 `clean_html_entities` 函式，自動清理子代理回傳中的 `&gt;` `&lt;` `&amp;` 等 HTML entity，無需主代理手動剝除。

**小書場景（≤12 子代理）替代方案：`emit_book_notes.py`**

`assemble_book_notes.py` 是為了支援 >12 子代理 + 骨架漸進填充的完整場景設計。對於小書（≤12 子代理 + 跳過 assemble 流程，見下方）主代理本應可以直接從 context 寫入，但手動 Write 8+ 個 15KB 分章 .md 仍會吃掉大量 context 和訊息輪次（實測 7-8 輪 = 浪費）。

**改用 `emit_book_notes.py`**（單一 Bash 指令取代 N 次 Write）：
```bash
uv run python3 $SCRIPTS/emit_book_notes.py "{tasks_dir}" "{專案輸出目錄}" "{年份}-{月份}-{書名}"
```

腳本自動：從所有 `.output` JSONL 取最終 assistant message → 清 HTML entity + code fence + 前言/後語 → 從 H1 `# Ch{N}: {title}` 解析章節號與章名 → 以 `{prefix}-Ch{N}-{title-slug}.md` 寫入專案目錄。與 `assemble_book_notes.py --use-h1` 產出的單檔相同，差別只在一次一檔而非合併。小書用 emit、大書用 assemble。

**等待期生產性工作：彙總骨架漸進填充**

子代理啟動後，主代理**禁止閒置等待**。在啟動子代理的**同一訊息**中，額外發出 Write 呼叫寫入彙總筆記骨架初版。骨架必須包含：

- ✅ Metadata block（書名、作者、出版年、核心論點、分章索引含連結）
- ✅ 所有必要區塊標題 + `<!-- 待填入 -->` 佔位符
- ✅ One Page Infograph 區塊標題 + 副標題

每收到一個子代理 completion，在**同一輪訊息**用 **Edit** 工具（非 Write）將該章 Top 1-3 Key Takeaway + Top 1 Key Quote 回填到骨架對應位置。當最後一個子代理完成時，骨架應已有 10-15 條 takeaway、8-10 條 quote 可供精選，最終彙總只需跨章去重、排序、補寫 Infograph。

**反面訊號**：若收到最後一個 completion 時骨架仍只有佔位符，代表整個等待期都在閒置。

**🔴 小書特例（≤12 子代理 + 跳過 assemble）：主代理自讀章節禁提前 Write**

小書場景中，主代理需自讀的 `<15KB` 章節（主代理撰寫的 Part 筆記），**禁止**在子代理等待期提前 Write 成 .md 檔。正確做法：
- 在 context 中起草筆記內容（回覆文字思考、Key Takeaway/Quote 清單）——這些進 context 不進磁碟
- 等全部子代理 completion 回來後，一次性精選並 Write 所有分章 + 彙總

違規症狀：收到 2-3 個子代理 completion 就急著「利用等待期」Write 主代理章節。違規後果：分章一旦定稿，彙總精選時難以平衡跨章 Top 素材分布（例如某章占彙總 50% Top Quote，但分章已寫完 emphasis 既定，彙總要重排需回去翻原文）；且違反 advisor 常給的「起草到 context 不 Write」建議。見 `feedback_small_book_no_early_write.md`。

#### 步驟 5：產出彙總筆記

所有分段筆記完成並寫入後，在主 context 中：

1. 讀取所有分段筆記（若子代理結果仍在 context 中，可直接使用）
2. 從各分段中再次篩選精華，按照同樣的輸出格式產出**彙總筆記**
3. 彙總筆記的特殊要求：
   - **區塊順序與分章一致**（Infograph 放最前作為全書 TL;DR）：分章索引 → **One Page Infograph Outline** → Key Takeaway → Call to Action → Mistakes & Lessons Learned → Unique Secret → Best Practice → Fun Story → Key Quote → 📖 折疊閱讀版。**禁止把 Infograph 放倒數第二**（舊規則已推翻，見 `feedback_summary_section_order.md`）
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
- **子代理 HTML entity 問題**：sonnet 子代理即使在 prompt 中明確禁止，仍高機率回傳 `&gt;`、`&lt;`、`&amp;` 等 HTML entity（實測違規率接近 100%）。**無需主代理手動清理**——`assemble_book_notes.py` 內建 `clean_html_entities` 函式自動處理。若不走 assemble 而手動 Write，則必須在寫入前手動剝除。
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

**必要區塊**（所有內容類型都必須輸出，以下為輸出順序）：
- One Page Infograph Outline
- Key Takeaway
- Key Quote

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
1. **預設**產出**三個 SRT 字幕檔**：
   - `*.en.srt` — 純英文字幕
   - `*.zh-tw.srt` — 純繁體中文字幕
   - `*.en&cht.srt` — 中英雙語字幕（每條字幕兩行：英文在上、繁體中文在下）

### 純中文來源特例（預設跳過 EN 翻譯）

若來源為**純中文內容**（判斷依據見下），**預設只產出一個 `.zh-tw.srt` 檔**，跳過整個 ZH→EN 翻譯 pipeline。使用者明確要求英文版才補做翻譯。

**判斷純中文來源的依據**（任一成立即視為純中文）：
- URL 為 Bilibili（`bilibili.com`、`b23.tv`）
- URL 為中國 podcast 平台（`ximalaya.com`、`lizhi.fm`、`qingting.fm`、`xiaoyuzhoufm.com`）
- Whisper STT 偵測到的語言為 `zh`
- 使用者明確表示內容為中文演講/訪談/podcast

**理由**：EN 翻譯 pipeline（split_batches → 11 個翻譯子代理並行 → extract → combine → merge）對純中文來源零價值——使用者讀中文筆記，英文 SRT 不會被看，卻耗用 ~14 分鐘 + 大量 API 呼叫。2026-04-11 樊登 11 本書 distill 的實測教訓。

**輸出調整**：
- 純中文來源跳過步驟 C（翻譯）與步驟 D（合併三檔），直接把清理後的 `.zh-tw.clean.srt` 重命名為最終 `.zh-tw.srt`
- markdown 筆記 metadata 只列 `.zh-tw.srt` 一個字幕檔

### 多 P playlist 特例（Bilibili anthology 等）

yt-dlp 對 Bilibili BV URL 預設會下載**整個 anthology**（多 P 影片）。若 `download.py` 輸出出現「Downloading playlist: ...」與「Downloading item X of N」，代表這是多 P 來源。

**判斷邏輯**：
- **N ≤ 3 P**：視為單一影片處理（concat 成 master SRT 沒問題，時間軸損失可接受）
- **N > 3 P**：走「多 P 分段流程」——每個分 P 獨立處理成一組 SRT + 獨立萃取，再產出彙總筆記

**多 P 分段流程**（N > 3）：
1. STT：用 `$SCRIPTS/multi_part_handler.py stt` 對所有分 P 批次執行 whisper
2. SRT 不 concat：**禁止**拼接成虛構 master SRT（2026-04-11 教訓：沒有合併影片，虛構時間軸對不到任何實體）
3. 萃取筆記：若分 P 內容差異大（每個分 P 是一個獨立主題/章節），**走「大型內容分段處理」流程**——為每個分 P 派一個子代理萃取，最後主代理寫彙總筆記
4. SRT 檔命名：`{prefix}-p01.zh-tw.srt`、`{prefix}-p02.zh-tw.srt` ... `-p{N}.zh-tw.srt`（每個分 P 獨立），**不產生**單一合併 SRT
5. 影音檔命名：`{prefix}-p01.mp4` ... `-p{N}.mp4`，統一存到 `download/`，用 `copy_files.py --multi-part` 或 `multi_part_handler.py copy` 批次複製

**preflight 快速檢測**：
```bash
# 只抓 playlist 規模與標題，不拉完整 format JSON（前者 ~100 bytes，後者 ~50 KB）
yt-dlp --cookies-from-browser chrome --flat-playlist --playlist-end 1 \
  -O "n_entries=%(playlist_count|1)s|title=%(title)s|duration=%(duration)s" "$URL"
```
若 `n_entries > 3`，先告知使用者「偵測到 N P playlist」再繼續（不需要等使用者回覆，直接繼續；僅告知）。

**注意**：一般非多 P 嫌疑的 URL 不需要跑此 preflight——`download.py` 內建的 `--dump-single-json` preflight 會在 stdout 印 `Downloading playlist` 等資訊，足以判斷。**只有已知 Bilibili BV URL 或其他多 P 嫌疑源才需要此外部 preflight**。

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

**多 P 影片專用腳本**：處理 Bilibili playlist 等多 P 來源一律用 `$SCRIPTS/multi_part_handler.py`，不要自寫 inline driver：
```bash
# 對所有 {TEMP}/{BVID}_p*.mp4 批次執行 Whisper STT（中文）
uv run python3 $SCRIPTS/multi_part_handler.py stt "{TEMP}" "{BVID}" --language zh

# 批次複製 MP4 到 download/，命名為 {prefix}-p01.mp4 ~ -p{N}.mp4
uv run python3 $SCRIPTS/multi_part_handler.py copy "{TEMP}" "{DOWNLOAD_DIR}" "{prefix}" "{BVID}"

# 批次複製 .zh-tw.clean.srt 到專案目錄，命名為 {prefix}-p01.zh-tw.srt ~ -p{N}.zh-tw.srt
uv run python3 $SCRIPTS/multi_part_handler.py copy-srt "{TEMP}" "{PROJECT_DIR}" "{prefix}" "{BVID}"
```

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

**⚠️ Bilibili BV URL 特別提醒**：Bilibili 的 `BV...` 網址若為多 P anthology，yt-dlp 預設會**下載全部 P**（已知問題）。`download.py` 目前未加 `--no-playlist`，因此多 P 影片會產出 `{BVID}_p1.mp4`、`{BVID}_p2.mp4`、... 等多檔；stdout 會印 `Downloading playlist: {name}` 和 `Downloading item X of N`。看到這兩行時代表是多 P 來源——走「多 P playlist 特例」流程（見上方），用 `multi_part_handler.py` 處理後續。

**判斷後續流程**：`download.py` 的 stdout 已包含所有判斷資訊（Title、Channel、Upload date、Duration、Description、`SUBS_AVAILABLE`），**不需要額外 `ls` 確認**。根據 `SUBS_AVAILABLE` 判斷：
- `YES`：有字幕，繼續步驟 B（去重清理）。**無影音檔需要處理。**
- `NO`：無字幕但有影音/音訊檔，**跳過步驟 B**，改用 Whisper STT 產生字幕。根據音訊時長選擇流程：

  **短音訊（<30 min）**：直接前台執行 `whisper_stt.py`：
```bash
uv run python3 $SCRIPTS/whisper_stt.py "/tmp/distill-{VIDEO_ID}/{VIDEO_ID}.{ext}" "/tmp/distill-{VIDEO_ID}" --language {語言代碼}
```

  **長音訊（>30 min）**：使用**三步驟前台工作流**（背景 Bash 任務寫入 /tmp/ 的檔案不會持久化，因此禁止一次性背景執行）：

  **Step 1：分段**（<5 秒，前台）
```bash
uv run python3 $SCRIPTS/whisper_stt_long.py "/tmp/distill-{VIDEO_ID}/{VIDEO_ID}.{ext}" "/tmp/distill-{VIDEO_ID}" --language {語言代碼} --split-only
```
  stdout 會印出 `SEGMENTS_DIR=...`、`SEGMENT_COUNT=N`、以及每段的 `SEG|{idx}|{path}|{duration}` 行。

  > **⚠️ 短音訊 fallback（30-45 min）**：`whisper_stt_long.py` 的預設 `--segment-minutes=45`，因此對 30-45 min 的音訊 `--split-only` **不會分段**，而是直接跑單次 mlx_whisper + OpenCC 並輸出 `.zh-tw.clean.srt`（stdout 會印「單次 mlx_whisper（短音訊，無需分段）」）。此情況下 **Step 2、Step 3 不需執行**，直接進到字元頻次預檢。若真的想強制分段可加 `--force-segment`。
  >
  > **Whisper 中段幻覺 recovery**：字元頻次預檢若發現「長行 >5 次」的幻覺 pattern（如固定 30 秒區間「對對對…」「嗯嗯嗯…」重複）**不要嘗試自清理**，改用 `feedback_whisper_midfile_hallucination_recovery.md` 流程：立刻 advisor + `ffmpeg volumedetect` 並行診斷 → `ffmpeg -ss` 切段 → `whisper_stt.py` 重跑 → `$SCRIPTS/patch_srt.py` 合併回原 SRT。

  **Step 2：逐段前台 Whisper**（每段 1-3 分鐘，逐個發 Bash 呼叫）
```bash
uv run python3 $SCRIPTS/whisper_stt.py "/tmp/distill-{VIDEO_ID}/tmp_segments/seg_000.mp4" "/tmp/distill-{VIDEO_ID}/tmp_segments" --language {語言代碼}
uv run python3 $SCRIPTS/whisper_stt.py "/tmp/distill-{VIDEO_ID}/tmp_segments/seg_001.mp4" "/tmp/distill-{VIDEO_ID}/tmp_segments" --language {語言代碼}
# ... 對 stdout 中列出的每段依序執行
```
  每段的 `whisper_stt.py` 會自動做：音量偵測 → mlx_whisper → 幻覺清理 → OpenCC 繁轉（中文）。

  **Step 3：合併**（<5 秒，前台）
```bash
uv run python3 $SCRIPTS/whisper_stt_long.py "/tmp/distill-{VIDEO_ID}/{VIDEO_ID}.{ext}" "/tmp/distill-{VIDEO_ID}" --language {語言代碼} --merge-only
```
  自動找到各段的 `.zh-tw.clean.srt`（中文）或 `.en.clean.srt`（英文），以各段實際時長計算 offset 合併，產出最終 `{basename}.zh-tw.clean.srt`。完成後自動清理 `tmp_segments/`。

  **三步驟流程的優點**：
  - 每步 <3 分鐘，**全部在前台完成**，檔案正常持久化
  - `whisper_stt.py` 已內建幻覺清理和 OpenCC，**不需要額外處理**
  - 零安全啟發式提示（全走 `uv run python3`）

  **STT 完成後字元頻次預檢**（見 `feedback_batch_preflight_before_subagents.md`）：
```bash
awk '{print length}' {txt_file} | sort -rn | uniq -c | head -5
```
  若最頻行長 ≤3 且佔比 >50%，該段大機率是 Whisper 幻覺區，需額外處理。清理完成後直接跳到步驟 C。

**Whisper 等待期生產性動作**（適用所有時長場景：短音訊單次 ~3-5 分鐘、長音訊三步驟總計 ~10 分鐘）：

啟動 Whisper（背景或前台逐段）後，主代理**禁止閒置等待**。在啟動 Whisper 的**同一訊息**或下一輪內並行發出：

1. **Read 既有同作者筆記前 30 行取結構**（若該作者已有 distill 筆記）—— 只取 metadata schema 與區塊順序，**不複製** bio/角色 framing/核心論點措辭（見 `feedback_avoid_stale_framing_propagation.md`）
2. **Glob 或 ls 確認作者目錄存在性**（避免後續 finalize 才發現要建目錄）
3. **預寫 markdown 筆記骨架**到專案目錄，只填 transcript-invariant 欄位：作者名、URL、時長、上傳日期、來源類型、字幕檔清單佔位符。bio/核心論點/Infograph 副標**延後**到 SRT 內容進 context 後再 Edit（見 `feedback_skeleton_defer_bio.md`）
4. **規劃 SRT sampling 計畫**：若 download.py stdout 的 description 含時間軸（≥6 段），預先把每段時間轉算 offset/limit（`secs × 2 ≈ entry`、`entry × 4 ≈ 行號`），準備 SRT 完成後**一次性同訊息並行 5-6 個 Read**（見 `feedback_srt_sampling_upfront_plan.md`）

**長音訊三步驟特有**（逐段 Whisper 各段間隙）：可用 Read 取 `{VIDEO_ID}.info.json` 前 5 行（雖然 download.py stdout 已有同樣資訊，但 info.json 的 description 不被 stdout 截斷）。

**反面訊號**：Whisper 完成通知回來時主代理只 Read 了 EP{N-1} 既有筆記、沒寫骨架、沒做 sampling 規劃 → 整個 ~5 分鐘等待期都在閒置，後續流程多 1-2 輪 round-trip。

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
2. **一次性啟動所有 Agent（不需要 Read agent_config.json）**：
   - `split_batches.py` 已輸出 N 個 `{VIDEO_ID}_prompt_batch_{i}.txt` 檔案，子代理會自行讀取這些檔案
   - 主代理**直接**對每個 batch（i=1..N）發一個 Agent call，不需要先 Read `agent_config.json`。參數如下：
     - `description`: `Translate SRT batch {i} EN→ZH`（或 `ZH→EN`，視翻譯方向）
     - `prompt`: 統一的 meta-prompt 模板（只有 `{i}` 和 prompt 檔路徑會變動），內容為：
       ```
       你是字幕翻譯子代理。請用 Read 工具讀取下方的 prompt 檔案，其中包含完整的翻譯任務說明和要翻譯的 SRT 檔案路徑。讀取後嚴格遵循其中的所有指示完成翻譯任務。

       Prompt 檔案路徑：{專案輸出目錄}/{VIDEO_ID}_prompt_batch_{i}.txt
       ```
     - `subagent_type`: `general-purpose`
     - `model`: `sonnet`
     - `mode`: `dontAsk`
     - `run_in_background`: `true`
   - **所有 N 個 Agent call 必須在同一個回覆中發出**（腳本 stdout 已提醒）
   - **嚴禁** `Read {VIDEO_ID}_agent_config.json`——agent_config 的內容可從本模板 + stdout 完全推得，Read 它只是冗餘的工具呼叫。見 `feedback_srt_read_budget.md`「不需要 Read agent_config.json」。

**🔴 子代理 prompt 中的詞彙替換規則（強制 sanity check）**

子代理 prompt 預設由 `split_batches.py` 產生（含通用翻譯規則）。**若主代理在 meta-prompt 或子代理 prompt 中加入「OldTerm → NewTerm」這類詞彙替換指令**，必須通過以下檢查：

1. **OldTerm 是否同時出現在 YouTube 標題或 description 中？** 標題與 description 是人為填的「真理層」（不是 STT 產物）。若 OldTerm 同時出現在標題/description 和字幕中，**它是真實名稱，禁止替換**。
2. **NewTerm 是否來自外部明確證據？** 不能基於「我訓練資料中的相似名」「發音類似」「不像主流產品」這類主觀理由。必須來自：標題明確的詞、description 明確的詞、Show Notes 連結、或使用者確認。
3. **不認識的專有名詞**：訓練截止日 (2026-01) 後可能新出現的產品/品牌——預設它是真實的新名稱，禁止替換為訓練資料中的相似名。
4. **真正的字幕誤聽才需要替換**——標誌：(a) 標題/description 用詞 ≠ 字幕用詞；(b) 字幕拼音明顯亂碼（如「Mark Andre」=Marc Andreessen、「chat GBT」=ChatGPT、「Replet」=Replit）。

**驗證 sample-first 時的限制**：sample-first（先跑 batch 1 驗證再啟動 2-N）只檢查格式（條目數、時間戳、code fence），**不驗證指令本身的正確性**——若指令是「替換真實產品名」，sample 也會「完美通過」，反而成為錯誤指令的快速擴散通道。詳見 `feedback_sample_first_no_command_validation.md`。

**advisor 也有盲區**：`advisor()` 看子代理 prompt 中的替換指令通常不會質疑——只要邏輯一致就放行。詳見 `feedback_advisor_blind_subjective_replacement.md`。

**finalize 時自動檢查**：`finalize_video_distill.py --check-title-terms` 會比對 YouTube 標題中的專有名詞與最終 SRT 出現次數，若標題詞在 .en.srt 出現多次但在 .zh-tw.srt 缺失，會警告（自動偵測錯誤替換）。**強烈建議所有影片 distill 都加這個 flag**。

**還原工具**：若已執行錯誤替換、需要還原，用 `$SCRIPTS/reverse_substitution.py` 一個指令完成（SRT 替換 + markdown 替換 + 檔案 rename）：
```bash
uv run python3 $SCRIPTS/reverse_substitution.py \
  "{專案輸出目錄}" "{錯誤的舊 prefix}" "{正確的新 prefix}" "{錯誤詞}" "{正確詞}"
```

**違反代價（實證）**：2026-04-21 OpenClaw episode（Lenny's Podcast × Claire Vo）主代理把 YouTube 標題明寫的「OpenClaw」替換為「Claude Code」（基於「OpenClaw 不在我訓練資料」這個主觀推測），6 個子代理執行了錯誤指令——279 條 SRT + 59 處 markdown + 4 個檔名 rename 修復。見 `feedback_distill_unknown_term_is_real.md`。

3. 等待**所有**子代理完成（系統會自動通知，**嚴禁輪詢** `ls` 檢查）

**🔴 等待期生產性工作（強制）**

啟動子代理後主代理**禁止閒置等待**。在啟動子代理的**同一訊息**中，額外並行發出以下工具呼叫以利用等待時間：

1. **Bash `wc -l "{srt_path}"`** — 取得原文 SRT 總行數，計算通讀需要的 Read 次數（英文 limit=500、中文 limit=300；`N = ceil(total_lines / limit)`）。**禁止憑感覺湊整數發 Read，必會超出檔案尾觸發 warning**
2. **N 個並行 Read** — 在同一訊息依 wc 結果通讀原文 SRT，為撰寫筆記做準備
3. **Write 筆記骨架初版** — 寫入 metadata block（作者、來源、日期、核心論點、字幕檔清單）、One Page Infograph 副標、所有必要與條件區塊的標題 + `<!-- 待填入 -->` 佔位符。作者姓名**以 download.py stdout 的 Show Notes 為準**（auto-caption 常誤聽外國姓氏，例如 Glyman→Lyman）

**讀 SRT 時即時捕獲引述**：遇到「X said」「as X put it」「Calvin said, look...」等引述訊號，立即在回覆的 text 中寫一個「引述清單」（`HH:MM X 引述者→真實講者 Y`），作為撰寫 Key Quote 歸屬的依據，避免把引述的他人觀點歸為講者本人。

**反面訊號**：若子代理全部完成時骨架仍只有佔位符、引述清單空白，代表整個等待期都在閒置，筆記品質和時間都會受損。

#### 🔴 收尾：一鍵完成 extract → combine → merge → copy → cleanup

**核心規則**：所有翻譯子代理完成後，**一律**用 `finalize_video_distill.py` 一個指令完成整個收尾。**嚴禁**分成 5 個獨立 Bash 呼叫（extract_translated_batches → combine_zh → merge → copy_files → cleanup）。

**為什麼禁止分步**：
- `combine_zh` 和 `merge` 有 producer-consumer 時序依賴（merge 讀 combine_zh 寫的 `zh.combined.srt`）；分步呼叫若誤放同訊息並行會損毀字幕
- 分步做法耗掉 5 個工具呼叫 + 5 次權限決策 + 大量 context tokens
- 正確串行邏輯已固化在 finalize 腳本內部

**執行指令**：
```bash
# EN→ZH 流程（預設，英文字幕為主軌）：
uv run python3 $SCRIPTS/finalize_video_distill.py \
  "{tasks_dir}" "/tmp/distill-{VIDEO_ID}" "{專案輸出目錄}" "{VIDEO_ID}" "{檔案名稱前綴}"

# ZH→EN 流程（中文字幕為主軌）：
uv run python3 $SCRIPTS/finalize_video_distill.py \
  "{tasks_dir}" "/tmp/distill-{VIDEO_ID}" "{專案輸出目錄}" "{VIDEO_ID}" "{檔案名稱前綴}" \
  --target-lang en --master zh --source-srt "/tmp/distill-{VIDEO_ID}/{中文clean檔名}"
```

- `{tasks_dir}`：從任一 task-notification 的 `<output-file>` 路徑取得父目錄
- `{檔案名稱前綴}`：例如 `2026-04-Ben-Horowitz-on-AI-Anxiety`
- 腳本依序執行：extract_translated_batches → combine_zh → merge → copy_files → cleanup，任一步失敗會中止並回報
- 可加 `--skip-cleanup` 保留 `/tmp/distill-{VIDEO_ID}/` 供後續除錯

> 下面的分步命令區塊（extract / combine / merge / copy / cleanup 各自 section）**僅在 finalize 某步失敗、需要手動除錯時**使用。正常流程不要走分步。

---

#### 分步回退（除錯用，一般流程跳過）

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

#### 步驟 D：產出三個版本的 SRT 字幕檔（⚠️ 分步除錯用，正常流程已被上方 finalize 腳本涵蓋）

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

#### 步驟 E：複製字幕和影音檔到最終位置（⚠️ 分步除錯用，正常流程已被上方 finalize 腳本涵蓋）

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

### 清理暫存檔（⚠️ 分步除錯用，正常流程已被上方 finalize 腳本涵蓋）

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
- **Write 前必做檔名衝突檢查**（見 `feedback_epub_session_conflict.md` 規則 6）：用 Glob 或 `ls "{作者目錄}/"` 確認目標檔名（含彙總檔）不存在。若已存在：
  - 內容近似（重跑同一來源）→ 請示使用者是否覆寫
  - 內容不同書（書名前綴撞車、檔名誤植、OPF vs 實際書名不一致）→ 加區分後綴（`-vol2`、書名全稱），避免無聲覆寫前一 session 的成果

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

### Output 1 → One Page Infograph Outline ⭐ 必要區塊
- 綜合萃取的內容，找出知識主題的脈絡
- 輸出一頁 Infograph 圖表的文字大綱
- 結構要求：
  - 📌 主標題 + 副標題
  - 3-5 個內容區塊，每個區塊含標題和 2-3 個重點
  - 底部金句（選自 Key Quote 中最具代表性的一句）
- 適合後續轉製為視覺化圖表
- **順序說明**：Infograph 放在最前面作為全篇摘要／TL;DR，讓讀者快速掌握整體脈絡；其餘區塊為詳細展開
- **撰寫時機**：雖然輸出順序在最前，實際撰寫時可在完成 Key Takeaway / Key Quote 等區塊後再回來補寫此區塊，以便挑出最具代表性的重點與金句

### Output 2 → Key Takeaway ⭐ 必要區塊
- 從內容中，歸納出最多 10 個 Key Takeaway
- 依照「重要性」由高至低排序
- 每個 takeaway 需包含：
  - **簡短標題**（粗體）
  - **深度說明**（2-3 句）：不只是「作者說了什麼」，而是「為什麼這很重要」和「對讀者的啟發」
- 萃取層次要求：事實（作者說了什麼）→ 意義（為什麼這很重要）→ 啟發（讀者可以從中學到什麼）
- 若內容有與主流看法不同之處，在相關 takeaway 中點出差異

### Output 3 → Call to Action 📋 條件區塊
- 從內容中，抓出最多 10 個可以具體操作執行的 Action，或是有潛力的投資創業機會
- 依照「可操作性、潛力性」由高至低排序
- 每個 action 需包含：
  - **具體行動標題**（粗體）
  - **做什麼**：明確的執行步驟，讀者看完就能動手
  - **為什麼**：預期效果或潛力說明
- **禁止**輸出「持續學習」「保持開放心態」等抽象建議

### Output 4 → Mistakes & Lessons Learned 📋 條件區塊
- 從內容中，抓出最多 10 個作者/講者明確承認的重大錯誤、失敗經驗或慘痛教訓
- 依照「教訓深度」由高至低排序
- 每個錯誤需包含：
  - **錯誤標題**（粗體）
  - **具體經過**：在什麼情境下、做了什麼決定、造成什麼後果
  - **教訓**：從這個錯誤中學到的具體原則或行為改變
- 必須是作者/講者**親身經歷**或**明確承認**的錯誤，不是泛泛的「應該避免的事」
- **禁止**把一般性建議改寫成「錯誤」，必須有真實的失敗故事或後果

### Output 5 → Unique Secret 📋 條件區塊
- 從內容中，抓出最多 10 個「有什麼跟其他多數人有不同看法，但講者卻覺得很重要的事實」
- 依照「與眾不同性」由高至低排序
- 嚴格格式：
  - 🔸 主流觀點：{大部分人相信的 X}
  - 🔹 講者洞見：{但講者發現事實是 Y}
  - 💡 為何重要：{這個差異帶來的影響}
- **禁止**把普通觀點包裝成「與眾不同」，必須是真正有反差的洞見

### Output 6 → Best Practice 📋 條件區塊
- 從內容中，抓出最多 10 個 Best Practice，或第一手親身經驗
- 重點聚焦在講者/作者的實際做法與實戰經驗
- 每個 practice 需包含：
  - **實踐標題**（粗體）
  - 具體做法描述，包含背景脈絡（在什麼情境下、怎麼做、效果如何）
- **禁止**輸出泛泛的「業界最佳實踐」，只收錄講者/作者親身驗證過的做法

### Output 7 → Fun Story 📋 條件區塊
- 從內容中，抓出最多 10 個有趣、好玩、或奇特的小故事
- 依照「有趣性」由高至低排序
- 每個故事需是內容中明確提到的具體事件或軼事
- **禁止**把論點改寫成「故事」，必須是真正的敘事性內容

### Output 8 → Key Quote ⭐ 必要區塊
- 從內容中，抓出最多 10 個令人印象深刻、或值得記住的 Quote
- 依照「易記性」由高至低排序
- 每個 quote 需包含：
  - 原文引用（保留原語言，使用 blockquote 格式）
  - 講者/作者歸屬
  - 繁體中文翻譯（若原文非中文）
  - 一句話說明為何此引用重要
- 優先選擇：具體生動的表述 > 抽象概念性的陳述

## Gotchas

以下是常見的錯誤模式，務必避免：

### 引用歸屬錯誤
作者/講者在文章中引用他人的話時，不要把被引用者的觀點歸為作者本人的觀點。Key Quote 區塊中必須正確標註說話者。如果作者說「正如 Paul Graham 所言：...」，這是 Paul Graham 的話，不是作者的話。

**Podcast cold open 特別處理**：訪談類 podcast 開頭常見 1-2 分鐘的 cold open 剪輯（挑選全集亮點快問快答），其中的台詞在正文中往往不會以同樣形式重現，難以直接對回「誰說的」。處理原則：
- 優先從 cold open 之後的正文段落（受訪者 intro 之後）找到相同觀點的出處，以該段落的歸屬為準
- 若正文確實沒有對應段落（純剪輯亮點），標註為「受訪者」或「主持人」而非具體姓名，或直接省略該 quote
- **禁止**憑「這句話像誰會說」的語氣臆測歸屬——訪談中主持人和受訪者常有觀點呼應

### Key Takeaway 流於表面
Key Takeaway 不是段落摘要。每個 takeaway 必須回答「為什麼這很重要？」和「這改變了什麼？」。如果一個 takeaway 可以套用在任何類似主題的文章上，那就太泛了——需要更具體。

### 條件性區塊全數輸出
Call to Action、Best Practice、Unique Secret、Fun Story、Mistakes & Lessons Learned 是條件性區塊。不是每篇文章都有這五種內容。在輸出前先問自己：「原文中真的有明確的第一手實踐經驗嗎？」如果沒有，就不要硬生出 Best Practice 區塊。「原文中真的有作者親身承認的錯誤嗎？」如果沒有，就不要硬生出 Mistakes & Lessons Learned 區塊。寧可少輸出，也不要捏造。

### 字幕擷取失敗未處理
影片/podcast 的字幕擷取可能因平台限制而失敗。如果 WebFetch 無法取得字幕，應改用可取得的文字內容（如文章描述、評論區摘要），並在筆記開頭註明「字幕無法擷取，以下基於可取得的文字內容」。不要因為字幕失敗就整個流程失敗。

## 語言

所有輸出使用繁體中文（zh-TW）。原文引用保留原語言，並附上繁體中文翻譯。

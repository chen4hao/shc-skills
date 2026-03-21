---
name: shc-distill
description: >
  當使用者提供 URL 並要求萃取重點、整理筆記、提取學習精華、summarize key takeaways
  時觸發。Use when user shares a URL and wants to extract insights, distill key
  takeaways, summarize learnings, or create study notes from articles, interviews,
  talks, videos, podcasts, essays, or blog posts.
---

# 萃取學習精華 (Distill)

**觸發條件**：使用者提供 URL 並要求萃取重點、整理筆記、提取學習精華。
**關鍵字**：distill, 萃取, 整理筆記, summarize, key takeaways, 學習重點

## 說明

從網路文章、訪談、演講、影片、podcast 中萃取學習重點精華，整理成結構化 markdown 筆記。
當來源為訪談影片或 podcast 時，會自動擷取完整字幕並存為三個 SRT 字幕檔：英文(*.en.srt)、繁體中文(*.zh-tw.srt)、中英雙語(*.en&cht.srt)。

## 輸出格式

詳細的輸出格式範例請參考 `templates/output-example.md`。

### 必要區塊

1. **Key Takeaway** — 最多 10 個，依重要性排序，含深度說明
2. **Key Quote** — 最多 10 個，保留原文並附繁體中文翻譯
3. **One Page Infograph Outline** — 適合轉製為視覺化圖表的大綱

### 條件性區塊（僅在內容確實存在時才輸出）

4. **Call to Action** — 具體可操作的行動建議
5. **Best Practice** — 講者/作者的第一手實踐經驗
6. **Unique Secret** — 與主流不同的獨特洞見
7. **Fun Story** — 有趣的故事或軼事

## 折疊閱讀版

在完整筆記末尾，附加一個以 `<details>` 標籤包裝的折疊版本：

- 用 `---` 與正文分隔
- 標題：`## 📖 折疊閱讀版`
- 每個 section 各自一個 `<details>` 區塊
- `<summary>` 格式：`**Section 名稱**（N 條）`
- 折疊內容為該 section 的精簡版（每條一行摘要）

## 儲存規則

- 儲存為 markdown 檔案
- 路徑格式：`{作者或來源名稱}/{年份}-{月份}-{簡短標題}.md`
- 所有輸出使用繁體中文（zh-TW），原文引用保留原語言並附翻譯

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

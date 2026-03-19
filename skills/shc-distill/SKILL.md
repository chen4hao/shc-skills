---
name: shc-distill
description: >
  萃取網路文章、訪談、演講、影片、podcast 的學習重點精華，整理成結構化 markdown
  筆記並儲存。當來源為訪談影片或 podcast 時，會自動擷取完整字幕並存為三個 SRT
  字幕檔：英文(*.en.srt)、繁體中文(*.zh-tw.srt)、中英雙語(*.en&cht.srt)。當使用者提供
  URL 並要求萃取重點、整理筆記、提取學習精華、summarize key takeaways 時觸發。Use
  when user shares a URL and wants to extract insights, distill key takeaways,
  summarize learnings, or create study notes from articles, interviews, talks,
  videos, podcasts, essays, or blog posts. When the source is an interview video
  or podcast, automatically extracts and saves three SRT subtitle files:
  English (*.en.srt), Traditional Chinese (*.zh-tw.srt), and bilingual
  (*.en&cht.srt).
---

# 萃取學習精華 (Distill)

**觸發條件**：使用者提供 URL 並要求萃取重點、整理筆記、提取學習精華。
**關鍵字**：distill, 萃取, 整理筆記, summarize, key takeaways, 學習重點

## 說明

從網路文章、訪談、演講、影片、podcast 中萃取學習重點精華，整理成結構化 markdown 筆記。

## 輸出格式

1. **Key Takeaway** — 最多 10 個，依重要性排序，含深度說明
2. **Key Quote** — 最多 10 個，保留原文並附繁體中文翻譯
3. **Call to Action** — 具體可操作的行動建議（條件性輸出）
4. **Best Practice** — 講者/作者的第一手實踐經驗（條件性輸出）
5. **Unique Secret** — 與主流不同的獨特洞見（條件性輸出）
6. **Fun Story** — 有趣的故事或軼事（條件性輸出）
7. **One Page Infograph Outline** — 適合轉製為視覺化圖表的大綱

## 儲存規則

- 儲存為 markdown 檔案
- 路徑格式：`{作者或來源名稱}/{年份}-{月份}-{簡短標題}.md`
- 所有輸出使用繁體中文（zh-TW），原文引用保留原語言並附翻譯

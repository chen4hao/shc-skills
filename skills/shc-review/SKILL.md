---
name: shc-review
description: >
  Code Review。Use when the user asks to review code changes, check code
  quality, or wants a thorough review before committing/merging.
---

# Code Review

**觸發條件**：使用者要求 review 程式碼變更、檢查品質、或在 commit/merge 前進行審查。
**關鍵字**：review, code review, 幫我看看, 檢查程式碼, review my changes

## 流程

1. 執行 `git diff` 查看所有未 commit 的變更（若沒有，則 review 最近一次 commit）
2. 逐檔檢查以下面向：
   - **正確性**：邏輯是否正確？有無邊界情況遺漏？
   - **安全性**：是否有 XSS、SQL injection、command injection 等漏洞？
   - **效能**：有無不必要的迴圈、重複計算、N+1 查詢？
   - **可讀性**：命名是否清楚？是否過度複雜？
   - **一致性**：是否符合專案現有的 coding style？
3. 以表格列出所有發現，標示嚴重程度（🔴 必修 / 🟡 建議 / 🟢 微調）
4. 最後給出整體評價和改善建議

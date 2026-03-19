---
name: shc-test
description: >
  撰寫與執行測試。Use when the user wants to write tests, add test coverage,
  or run existing tests for specific code.
---

# 撰寫與執行測試 (Test)

**觸發條件**：使用者要求撰寫測試、增加測試覆蓋率、或針對特定程式碼執行測試。
**關鍵字**：test, 測試, 寫測試, add tests, test coverage, unit test

## 流程

1. 先閱讀目標程式碼，理解其功能和邊界條件
2. 檢查專案中現有的測試框架和測試模式（檔案位置、命名慣例、assert 風格）
3. 撰寫測試，涵蓋：
   - ✅ Happy path（正常流程）
   - ❌ Edge cases（邊界情況）
   - 💥 Error cases（錯誤處理）
4. 執行測試並確認全部通過
5. 如果有測試失敗，修復程式碼或測試直到通過

請遵循專案現有的測試風格和慣例。

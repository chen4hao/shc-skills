---
name: shc-refactor
description: >
  安全重構。Use when the user wants to refactor code safely with a plan-first
  approach.
---

# 安全重構 (Safe Refactor)

**觸發條件**：使用者要求重構程式碼，採用先規劃再動手的安全方式。
**關鍵字**：refactor, 重構, restructure, 改善結構, clean up code, extract method

## 流程

1. **先理解**：閱讀目標程式碼和其所有呼叫方，完整理解現有行為
2. **制定計畫**：列出重構步驟，等待使用者確認後再動手
3. **執行重構**：
   - 每一步都保持功能不變（行為等價）
   - 小步前進，每個變更都可獨立驗證
   - 更新所有受影響的呼叫方和 import
4. **驗證**：執行現有測試確認沒有破壞任何東西
5. **摘要**：列出所有變更的檔案和修改原因

## 原則

- 不要同時改功能和改結構
- 如果沒有現有測試，先補測試再重構
- 保持 YAGNI — 不要為了「可能需要」而過度抽象

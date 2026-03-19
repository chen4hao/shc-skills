---
name: shc-commit-push-pr
description: >
  Commit, Push & 建立 PR。Use when the user wants to commit changes, push to
  remote, and create a pull request in one workflow.
---

# Commit, Push & 建立 PR

**觸發條件**：使用者要求一次完成 commit、push、建立 PR 的完整流程。
**關鍵字**：commit and push, 建PR, 開PR, create PR, push and PR, 送PR

## 流程

1. 執行 `git status` 和 `git diff` 檢視所有變更
2. 分析變更內容，撰寫簡潔有意義的 commit message（中英文皆可，視專案慣例而定）
3. 將相關檔案加入 staging 並 commit
4. Push 到遠端分支（若遠端分支不存在則建立）
5. 使用 `gh pr create` 建立 Pull Request，包含：
   - 簡短的標題
   - Summary 列點說明變更
   - Test plan 說明如何驗證

如果有未追蹤的敏感檔案（.env, credentials 等），跳過並警告使用者。

---
name: shc-git-summary
description: >
  Git 狀態摘要。Use when the user wants a quick overview of the current git
  repository status.
---

# Git 狀態摘要 (Git Summary)

**觸發條件**：使用者要求快速總覽目前 Git 倉庫的狀態。
**關鍵字**：git status, git summary, git 狀態, 目前分支, 現在什麼狀態, repo status

## 流程

執行以下指令並整理結果：

```bash
git status
git log --oneline -10
git branch -a
git stash list
```

以簡潔的格式呈現：
- 目前分支和最近 commit
- 未 commit 的變更數量
- 所有本地 / 遠端分支
- stash 列表
- 是否有未 push 的 commit

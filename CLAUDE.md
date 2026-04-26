# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

這是一個 **AI CLI Skills 集合**，透過 [Vercel Skills CLI](https://github.com/vercel-labs/skills) 發布，供 Claude Code、Codex CLI、Gemini CLI、Kiro CLI、GitHub Copilot 等 40+ 個 AI agent 使用。

不是一個可建置、可測試的軟體專案——純粹是 Markdown 定義的 skill prompts。

## 架構

```
skills/
  shc-{name}/
    SKILL.md        ← 每個 skill 的完整定義（唯一的檔案）
```

每個 `SKILL.md` 包含：
- **YAML frontmatter**：`name` 和 `description`（Vercel Skills CLI 用來註冊和觸發 skill）
- **Markdown body**：觸發條件、關鍵字、執行流程

## 安裝與管理

```bash
# 安裝所有 skills（全域）
npx skills add chen4hao/shc-skills -g --all

# 列出 repo 中的 skills
npx skills add chen4hao/shc-skills -l

# 列出已安裝的 skills
npx skills list

# 移除某個 skill
npx skills remove shc-review
```

## 編輯 Skills 的注意事項

- `description` 欄位是 AI agent 判斷何時觸發此 skill 的依據，需同時包含中英文觸發描述
- 命名慣例：資料夾和 name 都使用 `shc-` 前綴
- 所有使用者面向的輸出語言為繁體中文（zh-TW）
- Kiro 使用者需額外設定 `"skill://.kiro/skills/**/SKILL.md"` 在 agent resources 中

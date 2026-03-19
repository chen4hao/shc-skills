# SHC Skills

一組跨 AI CLI 工具的自訂工作流程 skills，透過 [Vercel Skills CLI](https://github.com/vercel-labs/skills) 統一管理與安裝。

## 安裝

```bash
npx skills add chen4hao/shc-skills -g
```

加上 `--all` 可安裝到所有已偵測到的 AI agent：

```bash
npx skills add chen4hao/shc-skills -g --all
```

## 包含的 Skills

| Skill | 說明 |
|-------|------|
| `shc-review` | Code Review — 逐檔檢查正確性、安全性、效能、可讀性 |
| `shc-debug` | 系統性除錯 — 重現、定位、分析根因、修復、驗證 |
| `shc-explain` | 解釋程式碼 — 含 ASCII 架構圖的深度解說 |
| `shc-refactor` | 安全重構 — 先規劃再動手，保持行為等價 |
| `shc-test` | 撰寫與執行測試 — 涵蓋 happy path、edge cases、error cases |
| `shc-techdebt` | 技術債掃描 — 重複程式碼、複雜度、過時依賴 |
| `shc-commit-push-pr` | 一鍵 Commit → Push → 建立 PR |
| `shc-git-summary` | Git 狀態快速摘要 |
| `shc-distill` | 萃取文章/影片/podcast 學習精華為結構化筆記 |

## 支援的 AI 工具

透過 Vercel Skills CLI 自動支援 40+ 個 AI agent，包括：

- Claude Code
- Codex CLI
- Gemini CLI
- Kiro CLI
- GitHub Copilot
- 以及更多...

## 管理

```bash
# 列出 repo 中的 skills
npx skills add chen4hao/shc-skills -l

# 列出已安裝的 skills
npx skills list

# 移除已安裝的 skills
npx skills remove shc-review
```

## Kiro 注意事項

Kiro CLI 使用者需在 `.kiro/agents/<agent>.json` 的 `resources` 欄位中加入：

```json
"skill://.kiro/skills/**/SKILL.md"
```

## License

MIT

# Claude Code Plugins & Skills 盤點與管理建議

> **審計日期：** 2026-03-24
> **環境：** macOS Darwin 24.6.0 / Claude Code（Opus 4.6 1M context）

---

## 一、完整盤點

### 已安裝 Plugins（4 個）

| Plugin | 來源 | 包含 Skills 數 | 狀態 |
|--------|------|---------------|------|
| `document-skills` | anthropic-agent-skills | 16 | ✅ 啟用 |
| `example-skills` | anthropic-agent-skills | 16 | ⚠️ 與 document-skills 完全重複 |
| `claude-api` | anthropic-agent-skills | 16 | ⚠️ 與 document-skills 完全重複 |
| `skill-creator` | claude-plugins-official | 8+ | ✅ 啟用 |

### Plugin 內含的 Skills 清單（共 16 個，三份重複）

| Skill | 用途 | 出現次數 |
|-------|------|---------|
| pdf | PDF 處理 | **×3** |
| docx | Word 文件 | **×3** |
| xlsx | Excel 試算表 | **×3** |
| pptx | PowerPoint 簡報 | **×3** |
| canvas-design | 視覺藝術設計 | **×3** |
| theme-factory | 主題樣式工廠 | **×3** |
| brand-guidelines | 品牌指南 | **×3** |
| frontend-design | 前端設計 | **×3** |
| algorithmic-art | 演算藝術 | **×3** |
| slack-gif-creator | Slack GIF 製作 | **×3** |
| webapp-testing | Web 應用測試 | **×3** |
| internal-comms | 內部通訊 | **×3** |
| doc-coauthoring | 文件共同撰寫 | **×3** |
| mcp-builder | MCP 伺服器建置 | **×3** |
| claude-api | Claude API 整合 | **×3** |
| skill-creator | Skill 建立工具 | **×4**（含 official） |

### 自訂 Commands（9 個）

位置：`~/.claude/commands/shc/`

| 指令 | 用途 |
|------|------|
| `/shc:review` | Code Review |
| `/shc:debug` | 系統性除錯 |
| `/shc:explain` | 程式碼解釋 |
| `/shc:refactor` | 安全重構 |
| `/shc:test` | 撰寫與執行測試 |
| `/shc:techdebt` | 技術債掃描 |
| `/shc:commit-push-pr` | Commit → Push → PR |
| `/shc:git-summary` | Git 狀態總覽 |
| `/shc:distill` | 內容萃取 |

### 自訂 Agents（6 個）

位置：`~/.claude/agents/`

| Agent | 用途 |
|-------|------|
| `shc-reviewer` | Code Review 審查者 |
| `shc-simplifier` | 程式碼簡化 |
| `shc-security` | 資安稽核（OWASP Top 10） |
| `shc-architect` | 系統架構設計 |
| `shc-mentor` | 程式教練 |
| `shc-verifier` | 建置與測試驗證 |

### 專案 Skills（9 個）

位置：`skills/shc-*/SKILL.md`（Vercel Skills CLI 格式，用於發布）

| Skill | 用途 |
|-------|------|
| shc-review | Code Review |
| shc-debug | 除錯模式 |
| shc-explain | 程式碼解釋 |
| shc-refactor | 安全重構 |
| shc-test | 測試撰寫 |
| shc-techdebt | 技術債掃描 |
| shc-commit-push-pr | Git 工作流程 |
| shc-git-summary | Git 狀態摘要 |
| shc-distill | 學習萃取 |

---

## 二、重複分析

### ❌ 重複 1：三個 Plugin 載入相同 16 個 Skills（嚴重）

```
document-skills  ──┐
example-skills   ──┼── 完全相同的 16 個 skills × 3 份
claude-api       ──┘
```

**影響：**
- 每個 skill 在系統提示中被列出 **3 次**（如本對話頂部的 available skills 清單所示）
- 浪費 context tokens（估計浪費 ~2000 tokens）
- 觸發時可能產生混亂（同名 skill 有 3 個版本）

**根因：** `anthropic-agent-skills` 市場的三個 plugin 共享同一批 skills，設計上是讓使用者只安裝其中一個。

### ⚠️ 重複 2：skill-creator 四重存在

`skill-creator` 出現在：
1. `document-skills` 內
2. `example-skills` 內
3. `claude-api` 內
4. `skill-creator@claude-plugins-official`（獨立安裝）

### ℹ️ 重複 3：shc 系列三重存在（合理）

| 位置 | 用途 | 保留？ |
|------|------|--------|
| `~/.claude/commands/shc/` | 個人使用的 slash commands | ✅ 保留 |
| `skills/shc-*/SKILL.md` | 發布給社群的 Vercel Skills | ✅ 保留（這是產品） |
| `.claude/shc-*/` | 專案本地 skill 命令 | ⚠️ 與全域 commands 可能衝突 |

---

## 三、建議的清理動作

### 動作 1：移除重複 Plugins（省 ~2000 tokens）

```bash
# 移除重複的 plugins，只保留 document-skills
claude plugins uninstall example-skills@anthropic-agent-skills
claude plugins uninstall claude-api@anthropic-agent-skills
```

**清理後保留：**
| Plugin | 來源 | 說明 |
|--------|------|------|
| `document-skills` | anthropic-agent-skills | 含 16 個通用 skills |
| `skill-creator` | claude-plugins-official | 官方 skill 建立工具 |

### 動作 2：檢查專案本地 `.claude/` 衝突

```bash
# 查看專案本地的 skill 命令是否與全域 commands 衝突
ls -la /Users/chen4hao/Workspace/aiProjects/shc-skills/.claude/
```

如果 `.claude/shc-*/` 的內容與 `~/.claude/commands/shc/` 相同，可考慮移除其中一邊避免衝突。

### 動作 3：驗證清理結果

```bash
# 確認剩餘 plugins
claude plugins list

# 在新會話中測試 skills 觸發是否正常
# 例如：提到 PDF 應只觸發 1 次，不是 3 次
```

---

## 四、管理最佳實踐

### 四種機制的定位

```
┌─────────────────────────────────────────────────┐
│                使用者的 Claude Code 環境           │
│                                                   │
│  Plugins（官方/社群）                              │
│  └─ 通用功能：文件處理、設計、測試等               │
│     安裝：claude plugins install                   │
│     管理：claude plugins list / uninstall          │
│                                                   │
│  Commands（個人捷徑）                              │
│  └─ 個人工作流程：/shc:review, /shc:debug 等      │
│     位置：~/.claude/commands/                      │
│     觸發：斜線指令 /shc:xxx                        │
│                                                   │
│  Agents（專業角色）                                │
│  └─ AI 角色代理：reviewer, architect, mentor 等    │
│     位置：~/.claude/agents/                        │
│     觸發：Agent 工具自動調派                       │
│                                                   │
│  Skills（發布產品）                                │
│  └─ 社群 Skills：shc-skills repo                  │
│     位置：skills/shc-*/SKILL.md                   │
│     發布：npx skills add chen4hao/shc-skills      │
└─────────────────────────────────────────────────┘
```

### 管理原則

1. **一個功能只應有一個主要來源** — 避免同名 skill 多重載入
2. **Plugin 優先** — 有官方 Plugin 的功能不需要另裝 Skill
3. **定期審計** — 每月執行 `claude plugins list` 檢查是否有新的重複
4. **命名空間隔離** — 自訂的用 `shc:` / `shc-` 前綴，與官方/社群區隔
5. **安全第一** — 只安裝信任來源的 plugins/skills（參考 Snyk ToxicSkills 報告，36% 第三方 skills 有漏洞）

---

## 五、清理前後對比

| 指標 | 清理前 | 清理後 |
|------|--------|--------|
| 已安裝 Plugins | 4 | 2 |
| 載入的 Skills 總數 | 16 × 3 + 8 = 56 | 16 + 8 = 24 |
| 重複 Skills | 32 個重複份 | 0 |
| 預估節省 tokens | — | ~2000 tokens/對話 |
| 觸發混亂風險 | 高 | 低 |

---

*最後更新：2026-03-24*

# Superpowers — AI CLI Skills 框架完整指南

> **來源：** [obra/superpowers](https://github.com/obra/superpowers)
> **作者：** Jesse Vincent / Prime Radiant
> **支援平台：** Claude Code、Cursor、Codex CLI、Gemini CLI、Kiro CLI 等 40+ AI agent

---

## 一、框架簡介

**Superpowers** 是一套完整的軟體開發工作流程框架，專為 AI coding agent 設計。它不是可編譯的軟體，而是以 Markdown 定義的 skill prompts 集合，涵蓋從需求設計、測試驅動開發、系統性除錯到程式碼審查的完整開發生命週期。

### 核心哲學

- **測試驅動開發** — 永遠先寫測試
- **系統性 > 臨時性** — 流程優於猜測
- **複雜度縮減** — 簡潔為首要目標
- **證據 > 宣稱** — 驗證才能宣稱完成

---

## 二、全部 14 個 Skills 一覽

| # | Skill 名稱 | 類型 | 說明 |
|---|-----------|------|------|
| 1 | brainstorming | 設計 | 協作式需求探索與設計規格制定 |
| 2 | writing-plans | 規劃 | 撰寫詳細實作計劃（檔案結構、任務分解） |
| 3 | using-git-worktrees | 工具 | 建立 git worktree 隔離開發環境 |
| 4 | test-driven-development | 開發 | 強制 RED-GREEN-REFACTOR 循環 |
| 5 | systematic-debugging | 除錯 | 四階段根因分析除錯法 |
| 6 | verification-before-completion | 品質 | 以證據驗證工作完成度 |
| 7 | requesting-code-review | 審查 | 調派 subagent 進行程式碼審查 |
| 8 | receiving-code-review | 審查 | 正確處理審查反饋的方法論 |
| 9 | subagent-driven-development | 開發 | 每任務獨立 subagent + 兩階段審查 |
| 10 | executing-plans | 執行 | 載入計劃並批量執行任務 |
| 11 | dispatching-parallel-agents | 執行 | 平行調派多個 agent 處理獨立問題 |
| 12 | finishing-a-development-branch | 整合 | 驗證 → 合併/PR → 清理 worktree |
| 13 | using-superpowers | 元技能 | 建立技能使用與優先級規則 |
| 14 | writing-skills | 元技能 | 用 TDD 方法撰寫新 skill |

---

## 三、安裝方式比較：Plugin vs Skill

| 比較項目 | Plugin（外掛市集） | Skill（Vercel Skills CLI） |
|---------|-------------------|--------------------------|
| **安裝指令** | `claude plugin install superpowers` | `npx skills add obra/superpowers -g --all` |
| **更新方式** | 自動隨市集版本更新 | 手動重新 `npx skills add` |
| **自訂彈性** | 低，無法修改 skill 內容 | 高，可 fork 後自訂每個 SKILL.md |
| **平台支援** | 僅限 Claude Code | 40+ AI agent（Claude Code, Cursor, Codex, Gemini CLI 等） |
| **離線使用** | 需連線驗證 | 本地檔案，完全離線可用 |
| **MCP 支援** | 內建 `use_browser` MCP 工具 | 需另外設定 MCP server |
| **社群生態** | 集中式，由官方維護 | 分散式，可自行擴充 |
| **適合對象** | 快速上手、只用 Claude Code 的使用者 | 進階使用者、多平台需求、需要客製化 |

### 建議

- **一般使用者** → Plugin 安裝最簡單，一行指令搞定
- **進階使用者 / 多平台** → Skill 安裝，可 fork 自訂，跨平台通用
- **團隊協作** → Skill 安裝，可納入 repo 統一管理

---

## 四、最推薦 Skills 速查表

以下精選 **8 個最實用的 skills**，依開發流程順序排列：

### 1. brainstorming（頭腦風暴）

| 欄位 | 內容 |
|------|------|
| **名稱** | brainstorming |
| **最佳用途** | 在寫任何程式碼之前，將模糊想法轉化為完整設計規格 |
| **流程** | 探索背景 → 逐一提問 → 提出 2-3 方案比較 → 分段呈現設計 → 審查迴圈（最多 3 次）→ 產出規格文件 |
| **實用場景** | 開發新功能前、重大架構決策、需求不明確時 |
| **範例** | 「幫我設計一個使用者通知系統」→ agent 會逐步問清需求（推播/Email/站內信？即時性？）→ 產出 `docs/superpowers/specs/notification-system.md` |

### 2. writing-plans（撰寫計劃）

| 欄位 | 內容 |
|------|------|
| **名稱** | writing-plans |
| **最佳用途** | 將規格拆解為可執行的小粒度實作步驟 |
| **流程** | 檔案結構映射 → 任務分解（每步 2-5 分鐘）→ 每步含完整代碼/測試/驗證 → 審查迴圈 → 交付 |
| **實用場景** | 多步驟功能開發、新人 onboarding、跨檔案重構 |
| **範例** | 「根據通知系統規格撰寫實作計劃」→ 產出包含 12 個步驟的計劃，每步列出檔案路徑、代碼範本、測試指令 |

### 3. test-driven-development（測試驅動開發）

| 欄位 | 內容 |
|------|------|
| **名稱** | test-driven-development |
| **最佳用途** | 強制 agent 遵循 TDD 紀律，避免先寫代碼後補測試 |
| **流程** | RED（寫最小失敗測試）→ 驗證紅色 → GREEN（寫最小通過代碼）→ 驗證綠色 → REFACTOR（清理重複）→ 重複 |
| **實用場景** | 所有功能開發、bug 修復、確保測試覆蓋率 |
| **範例** | 「實作 `calculateDiscount()` 函式」→ agent 先寫 `test_calculate_discount_returns_10_percent()` 看它失敗 → 再寫最小實作通過 |

### 4. systematic-debugging（系統性除錯）

| 欄位 | 內容 |
|------|------|
| **名稱** | systematic-debugging |
| **最佳用途** | 遇到 bug 時強制根因分析，杜絕猜測式修復 |
| **流程** | 根因調查（讀錯誤/重現/查 diff）→ 模式分析（找工作範例比較）→ 假設測試（最小化驗證）→ 實作修復（先寫失敗測試再修） |
| **實用場景** | 測試失敗、生產環境 bug、非預期行為 |
| **範例** | 「API 回傳 500 錯誤」→ agent 不會直接加 try-catch，而是追蹤 request → middleware → handler 的完整數據流，找到 null pointer 根因 |

### 5. verification-before-completion（完成前驗證）

| 欄位 | 內容 |
|------|------|
| **名稱** | verification-before-completion |
| **最佳用途** | 防止 agent 過早宣稱「完成」，要求提供實際證據 |
| **流程** | 辨認驗證指令 → 執行完整測試 → 讀取輸出與退出碼 → 確認結果 → 才能宣稱完成 |
| **實用場景** | 任何任務結尾、PR 提交前、部署前檢查 |
| **範例** | agent 修完 bug 後不會說「應該修好了」，而是跑完整測試套件並貼出 `42 passed, 0 failed` 的實際輸出 |

### 6. requesting-code-review（程式碼審查）

| 欄位 | 內容 |
|------|------|
| **名稱** | requesting-code-review |
| **最佳用途** | 自動調派 subagent 審查程式碼，在問題擴散前攔截 |
| **流程** | 取得 git SHA → 調派 code-reviewer subagent → 審查回報 → 關鍵問題立即修復 → 重要問題先修再繼續 |
| **實用場景** | 功能完成後、合併前品質把關、大型重構後 |
| **範例** | 完成通知系統後 → subagent 審查發現 SQL injection 風險 → 立即修復並重新驗證 |

### 7. subagent-driven-development（子 Agent 驅動開發）

| 欄位 | 內容 |
|------|------|
| **名稱** | subagent-driven-development |
| **最佳用途** | 大型任務拆分為獨立子任務，每任務由專屬 subagent 執行並審查 |
| **流程** | 分派任務 → 新 subagent 執行 → 兩階段審查（規格合規 + 代碼品質）→ 處理狀態（DONE/BLOCKED/NEEDS_CONTEXT） |
| **實用場景** | 多檔案功能開發、計劃執行、需要隔離上下文的任務 |
| **範例** | 10 步實作計劃 → 每步調派獨立 subagent → 機械任務用快速模型、架構決策用強力模型 → 自動品質審查 |

### 8. using-git-worktrees（Git 工作樹）

| 欄位 | 內容 |
|------|------|
| **名稱** | using-git-worktrees |
| **最佳用途** | 建立隔離開發環境，避免污染主分支 |
| **流程** | 偵測 worktree 目錄 → 驗證 gitignore → 建立 worktree → 執行專案設置（npm install 等）→ 驗證基線測試通過 |
| **實用場景** | 功能開發、實驗性改動、平行處理多個功能 |
| **範例** | 「開發通知功能」→ 自動建立 `.worktrees/feature-notifications` → 安裝依賴 → 確認測試綠色 → 開始開發 |

---

## 五、典型完整工作流程

```
使用者請求
    ↓
brainstorming → 設計核准
    ↓
writing-plans → 計劃核准
    ↓
using-git-worktrees → 建立隔離環境
    ↓
subagent-driven-development / executing-plans
    ├─ test-driven-development（每任務）
    ├─ systematic-debugging（遇 bug 時）
    ├─ requesting-code-review（每任務後）
    └─ verification-before-completion（驗證）
    ↓
finishing-a-development-branch → 合併或 PR
    ↓
✅ 完成
```

---

## 六、相關生態系統

| 專案 | 說明 |
|------|------|
| [superpowers-chrome](https://github.com/obra/superpowers-chrome) | 透過 DevTools Protocol 控制 Chrome，零依賴 |
| [superpowers-lab](https://github.com/obra/superpowers-lab) | 實驗性 skills（新技術與工具） |
| [superpowers-skills](https://github.com/obra/superpowers-skills) | 社群可編輯的 skills 庫 |
| [superpower-mcp](https://github.com/jmcdice/superpower-mcp) | 社群維護的 MCP server 實現 |

---

*最後更新：2026-03-24*

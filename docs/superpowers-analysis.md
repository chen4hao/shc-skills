# obra/superpowers — Jesse Vincent 的 TDD 開發方法論 Skills 分析報告

> 分析日期：2026-03-25
> 來源：[github.com/obra/superpowers](https://github.com/obra/superpowers)
> 作者：Jesse Vincent (Prime Radiant)
> ⭐ 111,119 | 🍴 8,918 | 授權：MIT | 版本：5.0.5

---

## 一、概述

Superpowers 是目前 **GitHub Stars 最高的 AI CLI skills 集合**（111K⭐），不只是 skill 工具箱——它是一套**完整的軟體開發方法論**，核心信仰：

> **"NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"**

共 **14 個 Skills** + **1 個 Agent** + **3 個 Hooks**，強制 AI agent 遵循 TDD-first 7 階段工作流。skills.sh 上最高安裝量達 **39.6K**（systematic-debugging），是「開發方法論」類 skills 的絕對王者。

---

## 二、7 階段核心工作流

```
① Brainstorming（蘇格拉底式問答，釐清設計）
    ↓
② Git Worktree（建立隔離工作區，確認基線乾淨）
    ↓
③ Writing Plans（拆解為極小任務，每個 2-5 分鐘）
    ↓
④ Subagent Execution（每任務派 subagent，雙階段 review）
    ↓
⑤ Test-Driven Development（RED → GREEN → REFACTOR）
    ↓
⑥ Code Review（spec compliance + code quality 分開審查）
    ↓
⑦ Finishing Branch（驗證通過 → merge/PR/保留/丟棄 四選項）
```

**關鍵特色**：此工作流**自動觸發**——skill 設定為「1% 機會適用就必須調用」，並內建大量「反合理化」表格，預先封堵 agent 跳過流程的藉口。

---

## 三、完整 Skills 清單

### 核心工作流 Skills（10 個）

| # | Skill | 安裝量 | 用途 |
|---|-------|--------|------|
| 1 | **using-superpowers** | 35K | 進入點：建立如何尋找和調用 skill 的規則 |
| 2 | **brainstorming** | — | 蘇格拉底式問答設計探索，一次一個問題，2-3 種方案 |
| 3 | **writing-plans** | — | 將設計拆解為極小任務（2-5 分鐘），含確切檔案、程式碼、驗證指令 |
| 4 | **executing-plans** | — | 批次執行計畫，帶人工 checkpoint |
| 5 | **subagent-driven-development** | — | 每任務派 subagent + 雙階段 review（spec + quality） |
| 6 | **dispatching-parallel-agents** | — | 2+ 個獨立任務並行執行 |
| 7 | **requesting-code-review** | 31.3K | 派發 code reviewer subagent |
| 8 | **receiving-code-review** | — | 接收 review 回饋的技術評估流程 |
| 9 | **using-git-worktrees** | — | 建立隔離 git worktree 工作區 |
| 10 | **finishing-a-development-branch** | — | 分支完成後整合決策（merge/PR/保留/丟棄） |

### 品質保證 Skills（3 個）

| # | Skill | 安裝量 | 用途 |
|---|-------|--------|------|
| 11 | **test-driven-development** | — | 強制 RED-GREEN-REFACTOR 循環，未經 TDD 的程式碼會被刪除 |
| 12 | **systematic-debugging** | 39.6K | 4 階段根因分析（最高安裝量） |
| 13 | **verification-before-completion** | — | 「Evidence before claims」— 完成前強制驗證 |

### Meta Skill（1 個）

| # | Skill | 用途 |
|---|-------|------|
| 14 | **writing-skills** | 建立新 skill 的指南，TDD 套用在文件寫作上 |

### Agent（1 個）

| Agent | 用途 |
|-------|------|
| **code-reviewer** | 資深 Code Reviewer，檢查計畫對齊度、程式品質、架構、文件、安全性 |

---

## 四、安全性評估

| 項目 | 結果 |
|------|------|
| 大部分內容 | ✅ 純 Markdown prompt（低風險） |
| Session hook | ⚠️ `hooks/session-start` bash 腳本每次自動執行，讀取本地檔案注入系統提示 |
| WebSocket Server | ⚠️ `brainstorming/scripts/server.cjs` 啟動本地 HTTP+WS 伺服器（僅 127.0.0.1，零外部依賴） |
| OpenCode Plugin | ⚠️ `.opencode/plugins/superpowers.js` 修改系統提示（transform hook） |
| 外部 API 呼叫 | ❌ 完全沒有 |
| 資料外送 | ❌ 完全沒有 |
| 遙測 | ❌ 完全沒有（與 gstack 不同） |
| 第三方依賴 | ❌ 零（WebSocket server 用純 Node.js 內建模組） |
| `curl \| bash` | ❌ 沒有 |
| **風險等級** | **🟢 低 — 接近純 Markdown，本地伺服器僅限 localhost** |

> **亮點**：在所有主要 skill 集合中（gstack、anthropics/skills、vercel/agent-skills），Superpowers 是**安全性最高的**——零遙測、零外部依賴、零網路請求。

---

## 五、Plugin vs Skill 安裝方式比較

Superpowers 同時支援兩種安裝方式：

| 比較項目 | Claude Code Plugin | Vercel Skills CLI |
|---------|-------------------|-------------------|
| 安裝指令 | `/plugin marketplace add obra/superpowers` | `npx skills add obra/superpowers -g` |
| 適用範圍 | Claude Code（含 hooks） | 42 個 AI agent |
| Hooks 支援 | ✅ session-start 自動注入 | ❌ 無 hooks 機制 |
| 自動觸發 | ✅ skill 自動觸發（1% 規則） | 視 agent 實作而定 |
| 跨平台 | ❌ | ✅ Cursor/Codex/Gemini/Kiro 等 |
| **建議** | **Claude Code 使用者首選（hooks 是殺手功能）** | 非 Claude Code agent 使用 |

> **結論**：若使用 Claude Code，強烈建議用 **Plugin 方式**安裝——`session-start` hook 是 Superpowers 自動觸發工作流的核心機制，Skills CLI 安裝無法享有此功能。

---

## 六、對應替代工具（競品/互補）

| Superpowers Skill | 最強替代方案 | 差異說明 |
|------------------|-------------|---------|
| brainstorming | gstack `/office-hours` | Superpowers 蘇格拉底式問答 vs gstack YC 六大問題 |
| test-driven-development | mattpocock/skills `tdd` (7.6K) | 兩者都是 RED-GREEN-REFACTOR，Matt 偏 TypeScript |
| systematic-debugging | gstack `/investigate` | Superpowers 4 階段分析 vs gstack 3 次失敗即停 |
| requesting-code-review | gstack `/review` / CodeRabbit | Superpowers 雙階段 review vs gstack 自動修復 |
| subagent-driven-development | gstack `/autoplan` | Superpowers 每任務派 agent vs gstack 三層串聯審查 |
| writing-plans | supercent-io `task-planning` (11.3K) | Superpowers 極小任務 vs supercent 管道式執行 |
| using-git-worktrees | shc-commit-push-pr | Superpowers 隔離 worktree vs shc 一鍵 commit→PR |
| verification-before-completion | （無直接競品） | Superpowers 獨有：完成前強制驗證 |

### 四大 Skill 集合定位比較

| 集合 | Stars | 取向 | 核心特色 |
|------|-------|------|---------|
| **obra/superpowers** | 111K | Engineering Discipline | TDD 至上、雙階段 review、反合理化 |
| **garrytan/gstack** | 45.5K | Product Shipping Velocity | 角色分工、內建瀏覽器、安全管控 |
| **mattpocock/skills** | 9.9K | TypeScript Craftsman | DDD、PRD-to-Issues、Obsidian 整合 |
| **anthropics/skills** | 102K | Official Reference | 文件處理、創意設計、開發工具鏈 |

---

## 七、最推薦 Skills 速查表

以下 7 個 Skill 最具獨特價值：

| 名稱 | 最佳用途 | 流程 | 實用場景 | 範例 |
|------|---------|------|---------|------|
| **systematic-debugging** | 系統性根因分析（安裝量最高 39.6K） | 4 階段：觀察症狀 → 形成假設 → 設計實驗 → 驗證根因 | 神秘 bug、間歇性問題、生產 incident | 「使用者回報某個 API 偶爾回 500」→ 系統性追蹤到 DB connection pool 耗盡 |
| **brainstorming** | 需求釐清與設計探索 | 蘇格拉底式問答 → 一次一個問題 → 2-3 種方案 → 取得核准 → 存設計文件 | 新功能啟動、重大架構決策 | 「我想加搜尋功能」→ 引導釐清：全文搜尋? 即時? 離線? 多語言? |
| **test-driven-development** | 強制 TDD 紀律 | RED（寫失敗測試）→ GREEN（最小程式碼通過）→ REFACTOR（改善但不改行為）| 核心業務邏輯、高風險模組 | 「實作付款計算邏輯」→ 先寫 10 個測試案例（含邊界），再寫實作 |
| **requesting-code-review** | 高品質雙階段 code review | 派發 reviewer subagent → ① spec compliance review → ② code quality review → 彙整報告 | PR 合併前、重要重構後 | 「review 這個 PR」→ 分別檢查「是否符合計畫」和「程式碼品質」 |
| **subagent-driven-development** | 並行執行多任務 + 自動審查 | 拆解計畫 → 每任務派 fresh subagent → 雙階段 review → 整合 | 大型功能開發、多檔案重構 | 「實作用戶管理 CRUD」→ 拆成 4 個子任務並行執行，各自 review |
| **writing-plans** | 將設計轉為可執行的極小步驟 | 拆解為 2-5 分鐘任務 → 每步含確切檔案/程式碼/驗證指令 | 複雜功能拆解、新手上手大型 codebase | 「實作 OAuth 整合」→ 拆成 15 個極小步驟，每步可獨立驗證 |
| **verification-before-completion** | 完成前強制驗證（無競品） | Evidence before claims → 跑測試 → 確認覆蓋率 → 驗證行為 → 才標記完成 | 任何宣稱「做完了」之前 | 防止 AI 說「我已經修好了」但實際沒跑測試的情況 |

---

## 八、與 shc-skills 的互補關係

| 面向 | shc-skills | Superpowers | 關係 |
|------|-----------|-------------|------|
| **哲學** | 獨立工具集，按需使用 | 強制性方法論，自動觸發 | 根本差異 |
| **TDD** | shc-test（可選） | 強制 RED-GREEN-REFACTOR | Superpowers 更嚴格 |
| **Code Review** | shc-review（輕量） | 雙階段 subagent review | Superpowers 更深入 |
| **除錯** | shc-debug（通用） | systematic-debugging (39.6K) | Superpowers 更結構化 |
| **Git** | shc-commit-push-pr、shc-git-summary | using-git-worktrees、finishing-branch | 互補（不同面向） |
| **重構** | shc-refactor（Plan Mode 先行） | 透過 TDD 保護的 refactor | 理念一致，工具不同 |
| **程式碼解釋** | ✅ shc-explain | ❌ | shc 獨有 |
| **技術債掃描** | ✅ shc-techdebt | ❌ | shc 獨有 |
| **知識萃取** | ✅ shc-distill | ❌ | shc 獨有 |
| **繁體中文** | ✅ | ❌ | shc 獨有 |
| **Brainstorming** | ❌ | ✅（含 Visual Companion） | Superpowers 獨有 |
| **Subagent 系統** | ❌ | ✅（核心設計） | Superpowers 獨有 |
| **反合理化機制** | ❌ | ✅（防止 agent 跳過流程） | Superpowers 獨有 |

> **最佳策略**：
> - **日常輕量工作** → shc-skills（快速 review、explain、debug、commit）
> - **嚴謹工程專案** → Superpowers（強制 TDD、雙階段 review、subagent 開發）
> - **兩者可共存**，shc 處理 Superpowers 未覆蓋的領域（explain、techdebt、distill、中文輸出）

---

## 九、核心洞察

> 1. **Superpowers 是安全性最高的主流 skill 集合**——零遙測、零外部依賴、零網路請求，幾乎純 Markdown
> 2. **111K⭐ 不是虛的**——systematic-debugging 39.6K 安裝量證明其方法論被廣泛認可
> 3. **Plugin 安裝優於 Skills CLI**——session-start hook 是自動觸發工作流的核心，只有 Plugin 方式支援
> 4. **「反合理化」設計是最大創新**——預先封堵 AI agent 跳過流程的所有藉口，值得所有 skill 作者學習
> 5. **適合重視可維護性的專案**，不適合快速 prototype（overhead 太重）；快速迭代場景用 gstack 或 shc-skills 更合適

---

*本報告由 Claude Code 自動生成*

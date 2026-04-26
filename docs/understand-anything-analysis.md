# Understand-Anything — Codebase 知識圖譜 Plugin 分析報告

> 分析日期：2026-03-28
> 來源：[github.com/Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything)
> 作者：Yuxiang Lin (Lum1104)，Georgia Tech 學生
> ⭐ 6,622 | 🍴 503 | 授權：MIT

---

## 一、概述

Understand-Anything 是一個 **Claude Code Plugin**（非 Vercel Skills CLI skill），將整個 codebase 分析成**互動式知識圖譜**，提供 React + Vite 視覺化儀表板。

核心功能：透過 5 個 sub-agent 的多代理管線（project-scanner → file-analyzer → architecture-analyzer → tour-builder → graph-reviewer）掃描專案，產生 `knowledge-graph.json`，然後基於此圖譜提供問答、差異分析、深入解釋、新人導覽等功能。

共 **6 個 Skills**，全部圍繞 codebase 理解。

---

## 二、完整 Skills 清單

| # | Skill | 指令 | 功能 |
|---|-------|------|------|
| 1 | **understand** | `/understand` | 核心指令。7 階段多代理管線分析整個 codebase，產生知識圖譜 |
| 2 | **understand-dashboard** | `/understand-dashboard` | 啟動 React Flow 互動式 web 儀表板（localhost:5173），視覺化知識圖譜 |
| 3 | **understand-chat** | `/understand-chat` | 基於知識圖譜回答 codebase 問題，Grep 搜尋 + 1-hop 展開 |
| 4 | **understand-diff** | `/understand-diff` | 分析 git diff 的漣漪效應，找出受影響的元件、層級、風險 |
| 5 | **understand-explain** | `/understand-explain [path]` | 深入解釋特定檔案/函式（架構層、內部結構、外部連接、資料流） |
| 6 | **understand-onboard** | `/understand-onboard` | 自動產生新人 onboarding 指南（架構、導覽、檔案地圖、複雜度熱點） |

### 多代理管線（/understand 核心流程）

```
Phase 1: PROJECT-SCANNER — 探索檔案、偵測語言/框架
    ↓
Phase 2: FILE-ANALYZER — 提取函式、類別、import、建立圖邊
    ↓
Phase 3: ARCHITECTURE-ANALYZER — 識別架構層（API/Service/Data/UI/Utility）
    ↓
Phase 4: TOUR-BUILDER — 產生按依賴順序的學習巡禮
    ↓
Phase 5: GRAPH-REVIEWER — 驗證圖的完整性與準確性
    ↓
Phase 6: DASHBOARD — 準備視覺化資料
    ↓
Phase 7: SAVE — 儲存 knowledge-graph.json，清理中間檔案
```

---

## 三、技術架構

**這是一個完整的 TypeScript monorepo，不是純 Markdown：**

```
understand-anything-plugin/
├── skills/              ← 6 個 SKILL.md（Markdown prompt）
├── agents/              ← Sub-agent prompt templates
├── src/                 ← TypeScript 原始碼
│   ├── context-builder/
│   ├── diff-analyzer/
│   ├── explain-builder/
│   ├── onboard-builder/
│   └── understand-chat/
├── packages/
│   ├── core/            ← 分析引擎（tree-sitter, Fuse.js, Zod）
│   └── dashboard/       ← React 18 + Vite + TailwindCSS v4 + React Flow + Zustand
└── homepage/            ← Astro 靜態網站
```

**主要依賴**：
- **core**：`fuse.js`（模糊搜尋）、`web-tree-sitter`（語法解析）、`zod`（schema 驗證）
- **dashboard**：`react` 18、`@xyflow/react`（圖譜視覺化）、`zustand`（狀態管理）、`@dagrejs/dagre`（自動佈局）、`vite`

---

## 四、安全性評估

| 項目 | 結果 |
|------|------|
| 可執行程式碼 | ⚠️ **有** — TypeScript 分析引擎 + React 儀表板 |
| Shell 腳本自動執行 | ⚠️ Sub-agent 會自動撰寫並執行分析腳本（find、wc、git ls-files 等） |
| `rm -rf` 指令 | ⚠️ Phase 7 清理 `.understand-anything/intermediate` 和 `/tmp`（範圍受限） |
| 本地 Web Server | ⚠️ Vite dev server 在 localhost:5173（不暴露外網） |
| 外部 API 呼叫 | ❌ 完全沒有（Fuse.js 本地搜尋，無 embedding API） |
| 資料外送 / 遙測 | ❌ 完全沒有 |
| `curl \| bash` | ❌ 沒有（安裝用 git clone + symlink） |
| 第三方 CDN | ❌ 沒有 |
| **風險等級** | **🟡 低～中 — 有腳本執行但範圍受限，零外部通訊** |

> **與其他集合的安全性比較**：
> - 比 gstack 安全（無遙測、無 cookie 匯入、無 `curl | bash`）
> - 比 Superpowers 稍高風險（有 TypeScript runtime + 自動執行腳本）
> - 與 anthropics/skills 風險相當（都有可執行程式碼但無惡意行為）

---

## 五、Plugin vs Skill 安裝方式比較

| 比較項目 | Claude Code Plugin（本 repo） | Vercel Skills CLI |
|---------|------------------------------|-------------------|
| 安裝指令 | `/plugin marketplace add Lum1104/Understand-Anything` | 不適用（本 repo 非 Skills CLI 格式） |
| 技術需求 | TypeScript runtime + pnpm | 無 |
| 儀表板功能 | ✅ React Flow 互動圖譜 | ❌ 純文字輸出 |
| 跨 agent 支援 | ✅ Claude/Codex/Gemini/Cursor/OpenCode 等 | ✅ 42 個 agent |
| 知識持久化 | ✅ knowledge-graph.json 可複用 | ❌ 每次重新分析 |
| 增量更新 | ✅ 只重分析變更的檔案 | ❌ |
| **建議** | **需要視覺化和持久化圖譜時用 Plugin** | 輕量理解需求用 shc-explain |

> **結論**：Understand-Anything 只能以 **Plugin 方式**安裝（它本身就是 Plugin 架構），不支援 Skills CLI。對於需要**深度理解大型 codebase** 的場景，Plugin 的持久化知識圖譜和互動儀表板是不可替代的優勢。

---

## 六、對應替代工具（競品/互補）

| Understand-Anything 功能 | 最強替代方案 | 類型 | 差異說明 |
|-------------------------|-------------|------|---------|
| /understand（codebase 分析） | **[codebase-to-course](https://github.com/zarazhangrui/codebase-to-course)** | Plugin | 同樣分析 codebase，但產出是 HTML 教學課程而非互動圖譜 |
| /understand-dashboard（視覺化） | **CodeTour** (VS Code) | Extension | CodeTour 手動建立導覽 vs UA 自動產生；CodeTour 無圖譜 |
| /understand-chat（問答） | **Cursor Chat** / **GitHub Copilot Chat** | IDE | IDE 內建 chat 更即時，但無知識圖譜做背景 |
| /understand-explain（解釋） | **shc-explain** | Skill | shc 輕量即時（含 ASCII 架構圖），UA 需先建圖但連結更豐富 |
| /understand-diff（影響分析） | **Code Analysis MCP**（80+ 工具） | MCP | MCP 更靈活，UA 有圖譜做漣漪分析 |
| /understand-onboard（新人導覽） | **CodeTour** (VS Code) | Extension | 手動 vs 自動產生 |
| 學術論文理解 | **PaperMCP**（ArXiv/Scholar） | MCP | UA 不做論文，PaperMCP 專攻學術 |

### 同類 Codebase 理解工具比較

| 工具 | Stars | 類型 | 輸出形式 | 前置需求 |
|------|-------|------|---------|---------|
| **Understand-Anything** | 6.6K | Plugin | 互動知識圖譜 + 儀表板 | 完整掃描 codebase |
| **codebase-to-course** | — | Plugin | 互動 HTML 教學課程 | 完整掃描 codebase |
| **shc-explain** | — | Skill | ASCII 架構圖 + 文字 | 無（即時分析） |
| **CodeTour** | — | VS Code | 步驟式導覽 | 手動建立 |
| **Code Analysis MCP** | — | MCP | 工具呼叫結果 | MCP 設定 |

---

## 七、最推薦 Skills 速查表

以下 5 個 Skill 各有獨特價值（全部 6 個中精選 5 個）：

| 名稱 | 最佳用途 | 流程 | 實用場景 | 範例 |
|------|---------|------|---------|------|
| **`/understand`** | 首次理解大型 codebase 全貌 | 5 個 sub-agent 依序掃描 → 建立知識圖譜 → 驗證完整性 → 儲存 JSON | 接手新專案、大型 codebase 探索、架構文件化 | 「幫我分析這個 monorepo 的架構」→ 產生完整知識圖譜，含所有模組、依賴、架構層 |
| **`/understand-dashboard`** | 視覺化瀏覽架構（殺手功能） | 載入 knowledge-graph.json → 啟動 Vite + React Flow → 互動式節點拖拽/搜尋/篩選 | 架構會議展示、新人 onboarding、技術決策 | 「開啟儀表板讓我看整體架構」→ 瀏覽器開啟互動圖譜，按層級上色，點擊節點看詳情 |
| **`/understand-diff`** | 評估程式碼變更的影響範圍 | 讀取 git diff → 對照知識圖譜找受影響節點 → 漣漪分析 → 風險評估 → 產出 diff-overlay.json | PR review 前評估風險、重構影響分析 | 「分析這個 PR 會影響哪些模組」→ 標出直接和間接受影響的元件，並評估風險等級 |
| **`/understand-explain`** | 深入理解特定模組的內外部關係 | 定位知識圖譜中的節點 → 展開架構層 + 內部結構 + 外部連接 + 資料流 | 修改不熟悉的模組前、code review 理解脈絡 | 「解釋 src/auth/middleware.ts 的角色」→ 顯示它在 API 層、連接 4 個服務、處理 JWT 驗證 |
| **`/understand-onboard`** | 為新成員自動產生入門指南 | 從知識圖譜提取 → 架構總覽 → 模組導覽 → 複雜度熱點 → 學習路徑 | 新人入職、外部顧問接手、開源專案貢獻者 | 「產生新人 onboarding 文件」→ 自動產出架構圖、關鍵模組說明、建議學習順序 |

---

## 八、與 shc-skills 的互補關係

| 面向 | shc-skills | Understand-Anything | 關係 |
|------|-----------|---------------------|------|
| **程式碼解釋** | ✅ shc-explain（輕量即時） | ✅ /understand-explain（需先建圖） | 互補：日常用 shc，深度用 UA |
| **架構視覺化** | ❌ | ✅ /understand-dashboard（React Flow） | UA 獨有殺手功能 |
| **新人導覽** | ❌ | ✅ /understand-onboard | UA 獨有 |
| **變更影響分析** | ❌ | ✅ /understand-diff | UA 獨有 |
| **Code Review** | ✅ shc-review | ❌ | shc 獨有 |
| **除錯** | ✅ shc-debug | ❌ | shc 獨有 |
| **測試** | ✅ shc-test | ❌ | shc 獨有 |
| **Git/PR** | ✅ shc-commit-push-pr | ❌ | shc 獨有 |
| **技術債** | ✅ shc-techdebt | ❌ | shc 獨有 |
| **知識萃取** | ✅ shc-distill（外部文章） | ❌ | shc 獨有（完全不同領域） |
| **繁體中文** | ✅ | ❌ | shc 獨有 |
| **安裝複雜度** | 低（純 Markdown） | 高（TypeScript + pnpm + React） | shc 更輕量 |

> **最佳策略**：shc-explain 處理日常的即時程式碼解釋需求；Understand-Anything 在**接手新專案、大型 codebase 探索、團隊 onboarding** 時啟用，產生持久化的知識圖譜供反覆查閱。兩者完全互補。

---

## 九、核心洞察

> 1. **互動式知識圖譜儀表板是唯一無替代品的殺手功能**——目前沒有其他 skill/plugin 提供 React Flow 視覺化 codebase 架構
> 2. **13 天 6,622⭐ 顯示強烈市場需求**——「理解大型 codebase」是開發者最常見的痛點之一
> 3. **skills.sh 安裝量僅 312 次**——因為它是 Plugin 格式而非 Skills CLI，且需要 TypeScript runtime，入門門檻較高
> 4. **安全性合理**——零外部通訊、零遙測，風險僅在本地腳本執行（分析用途）
> 5. **與 shc-skills 零競爭**——UA 專攻 codebase 理解/視覺化，shc 專攻 dev workflow；唯一小幅重疊是 explain 功能，但深度和定位不同

---

*本報告由 Claude Code 自動生成*

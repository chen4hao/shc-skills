# Vercel Skills — 官方 Skills 生態系分析報告

> 分析日期：2026-03-25
> 來源：[github.com/vercel-labs/skills](https://github.com/vercel-labs/skills)（CLI 工具）+ [github.com/vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)（Skills 內容）
> 作者：Vercel Labs

---

## 一、概述

Vercel Skills 生態由**三個 repo** 組成：

| Repo | Stars | 角色 |
|------|-------|------|
| `vercel-labs/skills` | 11,641 | CLI 工具（`npx skills`），管理 skill 安裝/發現 |
| `vercel-labs/agent-skills` | 23,779 | Vercel 官方 skills 集合（6 個） |
| `vercel-labs/next-skills` | 757 | Next.js 專屬 skills（3 個） |

CLI 支援 **42 個 AI agent**（Claude Code、Cursor、Codex、Gemini CLI、Kiro 等），是目前最通用的 skill 安裝工具。

---

## 二、完整 Skills 清單

### vercel-labs/agent-skills（6 個）

| # | Skill | 安裝量 | 用途 |
|---|-------|--------|------|
| 1 | **vercel-react-best-practices** | 244.8K | React/Next.js 效能最佳化，65 條規則 8 大分類（CRITICAL → LOW） |
| 2 | **web-design-guidelines** | 196.5K | UI 程式碼審查，100+ 條規則（a11y、效能、UX） |
| 3 | **vercel-composition-patterns** | — | React 組合模式（compound components、state lifting、避免 boolean prop 堆積） |
| 4 | **deploy-to-vercel** | — | 一鍵部署到 Vercel（含 `deploy.sh` 腳本） |
| 5 | **vercel-cli-with-tokens** | — | Vercel CLI token 認證操作指南 |
| 6 | **vercel-react-native-skills** | — | React Native/Expo 最佳實踐（清單效能、動畫、導航） |

### vercel-labs/next-skills（3 個）

| # | Skill | 用途 |
|---|-------|------|
| 7 | **next-best-practices** | Next.js 核心知識（RSC、async patterns、route handlers、metadata、image/font） |
| 8 | **next-upgrade** | Next.js 版本升級指引 |
| 9 | **next-cache-components** | Next.js 16 Cache Components 與 PPR |

### vercel-labs/skills CLI 內建（1 個）

| # | Skill | 安裝量 | 用途 |
|---|-------|--------|------|
| 10 | **find-skills** | 703K | 搜尋和安裝其他 skills |

---

## 三、安全性評估

| 項目 | 結果 |
|------|------|
| CLI 可執行程式碼 | ⚠️ TypeScript CLI 工具（simple-git、@clack/prompts 等依賴） |
| Telemetry 遙測 | ⚠️ 預設匿名收集使用數據到 `add-skill.vercel.sh/t`，可用 `DISABLE_TELEMETRY=1` 關閉 |
| Security Audit API | ✅ CLI 自動呼叫 `add-skill.vercel.sh/audit` 檢查 skill 安全評分 |
| deploy.sh 腳本 | ⚠️ 打包整個專案目錄上傳 Vercel（已排除 `.env`、`node_modules`、`.git`） |
| 外部 fetch | ⚠️ web-design-guidelines 從 GitHub raw content 動態載入規則 |
| Shell 指令執行 | ⚠️ deploy-to-vercel 包含 git/vercel CLI 指令 |
| 資料外洩模式 | ❌ 未發現 |
| 惡意指令 | ❌ 未發現 |
| **風險等級** | **🟡 低～中 — CLI 遙測需注意，其餘為正常功能** |

> **重點提醒**：
> - 安裝第三方 skills 時，CLI 的 audit API 會提供安全評分，但**最終仍依賴使用者判斷**
> - 使用 `deploy-to-vercel` 時注意專案中是否有敏感檔案未被排除
> - 建議設定 `DISABLE_TELEMETRY=1` 關閉遙測

---

## 四、Plugin vs Skill 安裝方式比較

| 比較項目 | Claude Code Plugin | Vercel Skills CLI (`npx skills`) |
|---------|-------------------|----------------------------------|
| 適用範圍 | 僅 Claude Code | **42 個 AI agent** |
| 安全管控 | Claude Code 權限系統 | Audit API 安全評分 |
| 安裝機制 | Plugin marketplace | Symlink / Copy 到 agent 目錄 |
| 發現機制 | Marketplace 搜尋 | `npx skills find` + skills.sh 排行榜 |
| 更新方式 | Marketplace 自動 | `npx skills update` |
| 生態規模 | 較小（Claude 專屬） | **31,000+ skills 流通中** |
| CLI 遙測 | 無 | ⚠️ 預設開啟（可關閉） |
| **建議** | 需要 Claude 權限管控時 | **跨 agent 使用 + 最大生態系首選** |

> **結論**：Vercel Skills CLI 是目前**最通用的 skill 管理工具**，生態規模最大。除非需要 Claude Code 特有的權限管控功能，否則建議使用 Skills CLI。

---

## 五、對應替代工具（Plugin / MCP / VS Code）

| Vercel Skill | 最強替代/互補工具 | 類型 | 差異說明 |
|-------------|------------------|------|---------|
| react-best-practices | **next-devtools-mcp**（Next.js 16 內建 MCP） | MCP | Skill 提供靜態規則，MCP 提供即時 logs/routes/metadata |
| web-design-guidelines | **ESLint** + **Prettier** | VS Code | Skill 更全面（含 a11y/UX），lint 工具偏格式/語法 |
| deploy-to-vercel | **Vercel CLI** (`vercel deploy`) | CLI | Skill 自動化決策流程，CLI 是底層工具 |
| composition-patterns | **mattpocock/skills** | Skill | Matt Pocock 的 TypeScript/React 架構 skills |
| react-native-skills | **Expo MCP Server** + **callstackincubator/agent-skills** | MCP+Skill | Expo MCP 提供截圖/DevTools，Callstack 提供 profiling 指南 |
| next-best-practices | **next-devtools-mcp** | MCP | MCP 可即時讀取 Next.js 專案狀態 |
| find-skills | **skills.sh** 排行榜 | 網站 | CLI 搜尋 vs 視覺化瀏覽 |

### skills.sh 全球排行榜 Top 10

| 排名 | Skill | 來源 | 安裝量 |
|------|-------|------|--------|
| 1 | find-skills | vercel-labs/skills | 703K |
| 2 | vercel-react-best-practices | vercel-labs/agent-skills | 244.8K |
| 3 | frontend-design | anthropics/skills | 196.8K |
| 4 | web-design-guidelines | vercel-labs/agent-skills | 196.5K |
| 5 | remotion-best-practices | remotion-dev/skills | 172.7K |
| 6 | azure-ai | microsoft/azure-skills | 144.2K |
| 7 | agent-browser | vercel-labs/agent-browser | 128.2K |
| 8 | azure-observability | microsoft/azure-skills | 115.5K |
| 9 | ai-image-generation | inferen-sh/skills | 110K |
| 10 | skill-creator | anthropics/skills | 104.8K |

---

## 六、最推薦 Skills 速查表

以下 7 個 Skill 最具實用價值（含 agent-skills + next-skills）：

| 名稱 | 最佳用途 | 流程 | 實用場景 | 範例 |
|------|---------|------|---------|------|
| **vercel-react-best-practices** | React/Next.js 效能最佳化 | AI 在寫/審查 React 程式碼時自動套用 65 條規則，依嚴重度分級（CRITICAL→LOW） | 開發 React app、PR review、效能調校 | 「幫我 review 這個 React 元件的效能問題」→ AI 自動檢查 waterfall、re-render、bundle size |
| **web-design-guidelines** | UI 程式碼品質審查 | 從外部載入 100+ 規則 → 逐項檢查 → 產出改善建議 | 上線前 UI 審查、a11y 合規檢查 | 「review 我的 UI 程式碼是否符合 web 最佳實踐」→ 檢查無障礙、效能、語意化 |
| **next-best-practices** | Next.js 核心開發指南 | 涵蓋 RSC、async patterns、directives、route handlers、metadata、image/font 優化 | 新專案架構決策、Next.js 新手上手 | 「我該用 Server Component 還是 Client Component？」→ 依場景給出正確指引 |
| **vercel-composition-patterns** | 解決 React 元件架構問題 | 識別 boolean prop 堆積 → 建議 compound components / render props / context 模式 | 元件庫設計、重構肥大元件 | 「這個 Button 元件已經有 15 個 props 了，幫我重構」→ 建議 compound component 模式 |
| **deploy-to-vercel** | 一鍵部署到 Vercel | 偵測框架 → 決策（git push / CLI / 無認證 fallback）→ 執行部署 → 回傳 URL | 快速上線 demo、部署 side project | 「部署這個 app 並給我連結」→ 自動選擇最佳部署方式 |
| **next-cache-components** | Next.js 16 快取與 PPR | 理解 Cache Components 概念 → 設定 PPR → 實作快取策略 | 升級 Next.js 16、優化頁面載入速度 | 「幫我把這個頁面改成用 Cache Components 來加速」 |
| **find-skills** | 發現和安裝新 skills | 使用者描述需求 → `npx skills find` 搜尋 → 推薦最佳匹配 → 安裝 | 不確定有什麼 skill 可用時 | 「有沒有幫我做 Stripe 整合的 skill？」→ 搜尋並推薦 |

---

## 七、與 shc-skills 的互補關係

| 分類 | shc-skills | Vercel Skills | 關係 |
|------|-----------|--------------|------|
| **Dev Workflow** | ✅ review, debug, test, commit, refactor | ❌ | shc 獨有優勢 |
| **程式碼解釋** | ✅ explain | ❌ | shc 獨有優勢 |
| **技術債掃描** | ✅ techdebt | ❌ | shc 獨有優勢 |
| **Git 操作** | ✅ git-summary, commit-push-pr | ❌ | shc 獨有優勢 |
| **知識萃取** | ✅ distill | ❌ | shc 獨有優勢 |
| **React 效能** | ❌ | ✅ react-best-practices (244.8K) | Vercel 獨有優勢 |
| **UI 審查** | ❌ | ✅ web-design-guidelines (196.5K) | Vercel 獨有優勢 |
| **Next.js 開發** | ❌ | ✅ next-best-practices, next-cache | Vercel 獨有優勢 |
| **元件架構** | ❌ | ✅ composition-patterns | Vercel 獨有優勢 |
| **部署** | ❌ | ✅ deploy-to-vercel | Vercel 獨有優勢 |
| **繁體中文** | ✅ | ❌ | shc 獨有優勢 |

> **最佳組合**：shc-skills（workflow + 中文）+ Vercel Skills（知識型最佳實踐 + 部署）= **完整的開發生態**。
> 兩者零重疊，完全互補。

---

## 八、核心洞察

> 1. **Vercel Skills CLI 是 skill 生態的基礎設施**——31,000+ skills、42 個 agent、703K find-skills 安裝量
> 2. **react-best-practices（244.8K 安裝）是全球最受歡迎的知識型 skill**，Vercel 工程團隊背書
> 3. **Skill 提供靜態知識，MCP 提供動態能力**——next-devtools-mcp 讓 AI 即時讀取 Next.js 專案狀態，與 skill 的靜態規則互補
> 4. **shc-skills 與 Vercel Skills 零重疊**——shc 專注 dev workflow + 中文，Vercel 專注框架知識 + 部署
> 5. **遙測預設開啟需注意**——建議設定 `DISABLE_TELEMETRY=1`

---

*本報告由 Claude Code 自動生成*

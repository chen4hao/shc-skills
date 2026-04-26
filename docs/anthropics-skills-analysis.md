# anthropics/skills — Anthropic 官方 Skills 分析報告

> 分析日期：2026-03-25
> 來源：[github.com/anthropics/skills](https://github.com/anthropics/skills)
> 作者：Anthropic（Claude 開發商）
> ⭐ 102,148 | 🍴 11,213

---

## 一、概述

共 **17 個 Skills**，分四大類：文件處理、創意設計、開發技術、企業溝通。
與前一份分析的 slavingia/skills（純 Markdown prompt）不同，**本 repo 包含實際可執行的 Python/Shell 腳本**。

安裝方式支援三種：
- **Claude Code Plugin Marketplace**：`/plugin marketplace add anthropics/skills`
- **Claude.ai**：付費方案已內建 example skills
- **Vercel Skills CLI**：`npx skills add anthropics/skills -g`

---

## 二、完整 Skills 清單

### 文件處理類（Proprietary 授權）

| # | Skill | 用途 | 包含腳本 |
|---|-------|------|---------|
| 1 | **docx** | Word 文件建立/讀取/編輯（docx-js + XML 操作） | `comment.py`, `accept_changes.py`, `unpack.py`, `pack.py` |
| 2 | **pdf** | PDF 全方位處理（合併/拆分/旋轉/浮水印/OCR/加密） | 依賴 pypdf, pdfplumber, reportlab, qpdf |
| 3 | **pptx** | PowerPoint 建立/編輯（pptxgenjs + XML 修改） | `thumbnail.py` |
| 4 | **xlsx** | Excel 建立/編輯/分析（openpyxl + pandas） | `recalc.py` |

### 創意設計類（Apache 2.0 授權）

| # | Skill | 用途 |
|---|-------|------|
| 5 | **algorithmic-art** | p5.js 演算法生成藝術 |
| 6 | **brand-guidelines** | 套用 Anthropic 品牌色彩與字型 |
| 7 | **canvas-design** | 靜態視覺藝術作品（海報/設計），輸出 .pdf/.png |
| 8 | **frontend-design** | 高品質前端介面設計（反對泛用 AI 風格） |
| 9 | **slack-gif-creator** | Slack 最佳化動態 GIF（含 Python 工具庫） |
| 10 | **theme-factory** | 10 個預設主題，套用到簡報/文件/HTML |

### 開發技術類（Apache 2.0 授權）

| # | Skill | 用途 |
|---|-------|------|
| 11 | **claude-api** | Claude API/SDK 完整開發指南（8 種語言） |
| 12 | **mcp-builder** | 建立 MCP Server 的指南與最佳實踐 |
| 13 | **skill-creator** | 建立/測試/最佳化新 skill 的 meta-skill |
| 14 | **web-artifacts-builder** | React + Tailwind + shadcn/ui 建置 claude.ai artifact |
| 15 | **webapp-testing** | Playwright 測試本地 web 應用程式 |

### 企業溝通類（Apache 2.0 授權）

| # | Skill | 用途 |
|---|-------|------|
| 16 | **doc-coauthoring** | 結構化文件共同撰寫（3 階段：收集 → 精煉 → 讀者測試） |
| 17 | **internal-comms** | 企業內部溝通範本（3P 更新、FAQ、事故報告等） |

---

## 三、安全性評估

| 項目 | 結果 |
|------|------|
| 可執行程式碼 | ⚠️ **有** — 多個 Python/Shell 腳本 |
| Shell 指令執行 | ⚠️ docx/xlsx/pptx 會呼叫 LibreOffice；web-artifacts-builder 會跑 `npm install` |
| npm 全域安裝 | ⚠️ docx skill 指示 `npm install -g docx` |
| 外部 CDN 引用 | ⚠️ algorithmic-art 載入 cdnjs.cloudflare.com 的 p5.js |
| WebFetch 外部資源 | ⚠️ claude-api / mcp-builder 會抓取 GitHub raw content |
| 子程序呼叫 | ⚠️ doc-coauthoring / skill-creator 會 spawn subagent |
| 資料外洩模式 | ❌ 未發現 |
| 惡意指令 | ❌ 未發現 |
| **風險等級** | **🟡 低～中 — 有程式碼執行但無惡意行為** |

> **緩解措施**：Claude Code 的權限系統會在執行 shell 指令、安裝套件時要求使用者確認。來源為 Anthropic 官方，可信度高。

---

## 四、Plugin vs Skill 安裝方式比較

| 比較項目 | Claude Code Plugin | Vercel Skills CLI |
|---------|-------------------|-------------------|
| 安裝指令 | `/plugin marketplace add anthropics/skills` | `npx skills add anthropics/skills -g` |
| 適用範圍 | 僅 Claude Code | 40+ AI CLI agents |
| 安全管控 | Claude Code 權限系統逐一確認 | 無內建權限控管 |
| 更新方式 | Plugin marketplace 自動 | `npx skills update` |
| 腳本執行 | 整合度高（直接呼叫） | 需自行處理依賴 |
| **建議** | **含腳本的 skill（docx/pdf/pptx/xlsx）用 Plugin** | 純 prompt skill 用 Skills CLI |

> **結論**：文件處理類（含 Python 腳本）建議用 **Plugin 方式**安裝，因 Claude Code 權限系統能控管腳本執行。純 prompt 類 skill 若需跨 agent 使用，則 **Skills CLI** 較佳。

---

## 五、對應替代工具（Plugin / MCP / VS Code）

| 類別 | anthropics/skills | 最強替代方案 | 差異說明 |
|------|------------------|-------------|---------|
| 文件處理 | docx, pdf, pptx, xlsx | 無直接競品（獨佔優勢） | Anthropic 獨家，文件類最完整 |
| Code Review | （無） | **CodeRabbit** (VS Code) / `code-review` 官方 plugin | 官方 plugin 有 5 個平行 Sonnet agent |
| 前端設計 | frontend-design | **v0.dev** / Bolt.new | v0 直接產出程式碼，skill 提供設計原則 |
| MCP 建構 | mcp-builder | **FastMCP** 框架 | FastMCP 是實際框架，skill 是建構指南 |
| API 開發 | claude-api | Anthropic SDK 文件 | skill 整合了 8 語言範例，比查文件快 |
| Web 測試 | webapp-testing | **Playwright MCP Server** | MCP 更靈活，skill 更結構化 |
| Skill 開發 | skill-creator | **obra/superpowers** plugin | Superpowers 42K⭐，含完整 dev workflow |
| 安全稽核 | （無） | **Trail of Bits** skills / Aikido | 專業安全工具更深入 |
| 技術債 | （無） | **CodeScene** (VS Code) | 專門的技術債分析引擎 |

---

## 六、最推薦 Skills 速查表

以下 8 個 Skill 最具獨特價值且實用性高：

| 名稱 | 最佳用途 | 流程 | 實用場景 | 範例 |
|------|---------|------|---------|------|
| **pdf** | PDF 全方位處理（合併/拆分/OCR/加密） | 讀取 → 判斷操作類型 → 執行（pypdf/reportlab/qpdf）→ 驗證輸出 | 合約合併、報告拆分、掃描 PDF 文字化 | 「把這 5 個 PDF 合併成一個，加上頁碼和浮水印」 |
| **docx** | Word 文件自動化產生與編輯 | 新建用 docx-js / 編輯用 XML unpack → 修改 → repack | 自動產生報告、批量修改合約、處理追蹤修訂 | 「讀取這份 Word 檔，接受所有修訂並更新目錄」 |
| **xlsx** | Excel 分析與自動化 | 讀取 → openpyxl/pandas 處理 → 公式驗證 → 輸出 | 財務模型建立、數據清洗、圖表產生 | 「分析這份銷售報表，加上 YoY 成長率欄位和圖表」 |
| **claude-api** | 快速建置 Claude API 應用 | 選語言 → 參考範例 → 實作（含 tool use/streaming/batch） | 建置 chatbot、整合 AI 到現有系統、Agent 開發 | 「用 TypeScript 建一個支援 tool use 的 Claude agent」 |
| **mcp-builder** | 建立 MCP Server 整合外部服務 | 深度研究 API → 實作 server → 審查/測試 → 評估 | 為內部 API 建 MCP 接口、整合第三方服務 | 「幫我建一個連接 Jira API 的 MCP Server」 |
| **frontend-design** | 產出有設計感的前端介面 | 分析需求 → 選擇字型/配色/佈局 → 實作 → 細節打磨 | Landing page、Dashboard、元件庫建置 | 「設計一個深色主題的 SaaS Dashboard，避免 AI 風格」 |
| **skill-creator** | 建立與最佳化自訂 Skill | 撰寫 SKILL.md → 寫測試 prompt → 跑 eval → benchmark → 迭代 | 為團隊建立專屬 workflow skill | 「幫我建一個自動化 DB migration review 的 skill」 |
| **doc-coauthoring** | 結構化共同撰寫文件 | 語境收集（info dump + 追問）→ 逐節精煉 → 讀者測試 | 技術規格書、提案、決策文件 | 「我要寫一份微服務遷移提案，先幫我收集所有需要的背景」 |

---

## 七、與 shc-skills 的互補關係

| shc-skills | anthropics/skills 對應 | 關係 |
|-----------|----------------------|------|
| shc-review | （無，但有官方 plugin `code-review`） | 互補：shc 提供中文 review，官方 plugin 有多 agent 審查 |
| shc-debug | （無，但有官方 plugin `debugger`） | 互補 |
| shc-test | webapp-testing | 互補：shc 偏通用測試，官方偏 Playwright Web 測試 |
| shc-commit-push-pr | （無） | shc 獨有優勢 |
| shc-explain | （無） | shc 獨有優勢 |
| shc-techdebt | （無） | shc 獨有優勢 |
| shc-refactor | （無） | shc 獨有優勢 |
| shc-git-summary | （無） | shc 獨有優勢 |
| shc-distill | （無） | shc 獨有優勢 |
| （無） | docx, pdf, pptx, xlsx | 官方獨有：完整文件處理能力 |
| （無） | claude-api, mcp-builder, skill-creator | 官方獨有：開發者工具鏈 |
| （無） | frontend-design, algorithmic-art, canvas-design | 官方獨有：創意設計類 |

> **最佳組合建議**：同時安裝 shc-skills（dev workflow + 中文輸出）+ anthropics/skills（文件處理 + 創意設計 + 開發工具鏈），形成互補的完整生態。

---

## 八、核心洞察

> 1. **文件處理四件套（docx/pdf/pptx/xlsx）是殺手級功能**——目前無替代品，且為 Proprietary 授權
> 2. **含可執行腳本 ≠ 不安全**——Claude Code 權限系統會攔截，且 Anthropic 官方來源可信度最高
> 3. **開發者工具鏈（claude-api + mcp-builder + skill-creator）** 對想擴展 AI 能力的開發者價值極高
> 4. **shc-skills 在 dev workflow 和繁體中文輸出上具有不可替代的差異化優勢**

---

*本報告由 Claude Code 自動生成*

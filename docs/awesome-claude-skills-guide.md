# Awesome Claude Skills — ComposioHQ 精選集合完整指南

> **來源：** [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)
> **維護者：** ComposioHQ（Series A $29M 融資，10 萬+ 開發者用戶）
> **性質：** 社群精選集合（非 Anthropic 官方認可）
> **規模：** 60+ 獨立 Skills + 800+ Composio SaaS 自動化整合

---

## 一、專案簡介

**awesome-claude-skills** 是由 ComposioHQ 維護的精選 Claude Skills 集合，匯集了社群貢獻的各種實用 skills，涵蓋文件處理、開發工具、資料分析、商業行銷、創意媒體、安全工具等多個領域。

### ComposioHQ 背景

- 2023 年成立於舊金山
- 2025 年 3 月 Series A 融資 $29M（Lightspeed Venture Partners 領投）
- 核心業務：為 AI agent 提供 1000+ 工具連接層
- 客戶包括 Glean、Databricks、YC 新創等 200+ 企業

---

## ⚠️ 二、安全性評估（重要）

### 第三方 Skills 的安全風險

根據 **Snyk ToxicSkills 審計**（2026 年 2 月），針對 3,984 個第三方 skills 的掃描結果：

| 風險指標 | 數據 |
|---------|------|
| 至少一個安全漏洞 | **36.82%** |
| 包含關鍵級別漏洞 | **13.4%** |
| 已確認惡意 skills | **76 個** |
| 惡意 skills 結合提示注入+惡意軟體 | **91%** |

### 已知攻擊手法

- 認證信息竊取（API keys、tokens）
- 後門安裝（透過 shell 指令）
- 資料外洩（將敏感資訊傳送到外部）
- Skills 通過**直接注入指令到系統提示**運作，本質上是「設計內的提示注入」

### Anthropic 官方建議

> **「我們強烈建議您要麼撰寫自己的 skills，要麼使用來自您信任的提供商的 skills。」**

### 安全使用建議

1. **安裝前必讀 SKILL.md 全文**，檢查是否有可疑的 shell 指令、外部 URL、資料傳送
2. **優先使用 Anthropic 官方 skills**：[github.com/anthropics/skills](https://github.com/anthropics/skills)
3. **不要盲目安裝整個集合**，只挑選需要且審查過的個別 skill
4. **檢查 skill 是否要求過大權限**（如 shell 存取、檔案系統寫入、網路請求）
5. **Composio Connect 需要 API key**，確認只授權必要的應用

---

## 三、Skills 分類總覽

### 60+ 獨立 Skills

| 類別 | 數量 | 代表性 Skills |
|------|------|--------------|
| 文件處理 | 5 | docx, pdf, pptx, xlsx, Markdown→EPUB |
| 開發工具 | 20+ | artifacts-builder, aws-skills, MCP Builder, TDD, git-worktrees |
| 資料分析 | 4 | CSV Summarizer, deep-research, postgres, root-cause-tracing |
| 商業行銷 | 5 | Brand Guidelines, Competitive Ads, Domain Brainstormer, Lead Research |
| 通訊寫作 | 7 | brainstorming, Content Research, Meeting Insights, Twitter Optimizer |
| 創意媒體 | 7 | Canvas Design, imagen, Image Enhancer, Slack GIF, Video Downloader |
| 生產力 | 8 | File Organizer, Invoice Organizer, kaizen, Resume Generator |
| 協作管理 | 5 | git-pushing, google-workspace, outline, review-implementing |
| 安全系統 | 4 | computer-forensics, file-deletion, metadata-extraction, threat-hunting |

### 800+ Composio SaaS 整合

透過 Composio Connect 插件，可連接：

| 類別 | 應用範例 |
|------|---------|
| CRM | HubSpot, Salesforce, Pipedrive, Zoho |
| 專案管理 | Asana, Jira, Linear, Notion, Trello, ClickUp |
| 通訊 | Slack, Discord, Teams, Telegram, WhatsApp |
| 程式碼/DevOps | GitHub, GitLab, Sentry, Vercel, Datadog |
| 電子郵件 | Gmail, Outlook, SendGrid |
| 社群媒體 | Twitter, LinkedIn, Instagram, TikTok, YouTube |
| 電商/付款 | Shopify, Stripe, Square |
| 設計 | Figma, Canva, Miro, Webflow |
| 分析 | Google Analytics, Mixpanel, PostHog, Amplitude |

---

## 四、安裝方式比較：Plugin vs Skill

| 比較項目 | Plugin（外掛市集） | Skill（手動安裝） |
|---------|-------------------|------------------|
| **可用性** | 部分 skills 有對應 Plugin（如 docx, pdf, xlsx） | ✅ 全部可用 |
| **安裝方式** | `claude plugin install <name>` | `cp -r skill-name ~/.config/claude-code/skills/` |
| **安全審查** | 經過市集基本審查 | ❌ 無審查，需自行檢查 |
| **更新方式** | 自動更新 | 手動更新 |
| **自訂彈性** | 低 | 高，可直接改 SKILL.md |
| **Composio 整合** | 需另裝 Connect 插件 | 需另裝 Connect 插件 |

### 與已知的 Plugin 對應關係

| Skill | 對應 Plugin | 建議 |
|-------|------------|------|
| docx | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| pdf | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| pptx | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| xlsx | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| artifacts-builder | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| Brand Guidelines | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| Slack GIF Creator | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| Theme Factory | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| Canvas Design | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| MCP Builder | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| Internal Comms | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| Webapp Testing | ✅ Anthropic 官方 document-skills | **用 Plugin**（官方維護） |
| Skill Creator | ✅ Anthropic 官方 skill-creator | **用 Plugin**（官方維護） |
| TDD | ✅ Superpowers Plugin | **用 Plugin**（社群熱門） |
| brainstorming | ✅ Superpowers Plugin | **用 Plugin**（社群熱門） |
| subagent-driven-dev | ✅ Superpowers Plugin | **用 Plugin**（社群熱門） |
| git-worktrees | ✅ Superpowers Plugin | **用 Plugin**（社群熱門） |
| deep-research | ❌ 無 Plugin | 審查後用 Skill |
| Composio Connect | ❌ 無 Plugin | 審查後用 Skill（需 API key） |

### 建議

- **有對應官方 Plugin 的** → 優先用 Plugin（安全、自動更新）
- **無 Plugin 但實用的** → 仔細審查 SKILL.md 後手動安裝
- **Composio 800+ 整合** → 適合需要跨 SaaS 自動化的使用者，但需評估 API key 權限風險

---

## 五、最推薦 Skills 速查表

以下精選 **8 個最實用且安全風險較低的 skills**（排除已有官方 Plugin 對應的）：

### 1. deep-research（深度研究）

| 欄位 | 內容 |
|------|------|
| **名稱** | deep-research |
| **最佳用途** | 利用 Gemini Deep Research Agent 進行多步驟深度研究 |
| **流程** | 定義研究問題 → 調用 Gemini 研究代理 → 多輪搜尋與分析 → 產出結構化研究報告 |
| **實用場景** | 技術選型調研、競品分析、學術文獻回顧、市場趨勢研究 |
| **範例** | 「研究 2026 年 Rust vs Go 在微服務的優劣」→ agent 進行多步驟網路研究 → 產出含引文的比較報告 |

### 2. postgres（PostgreSQL 查詢）

| 欄位 | 內容 |
|------|------|
| **名稱** | postgres |
| **最佳用途** | 安全地對 PostgreSQL 資料庫進行唯讀查詢與分析 |
| **流程** | 連接資料庫 → 理解 schema → 撰寫 SQL → 執行唯讀查詢 → 分析結果 |
| **實用場景** | 資料探索、報表生成、效能分析、資料品質檢查 |
| **範例** | 「分析上個月的使用者註冊趨勢」→ agent 查詢 users 表 → 按日/週聚合 → 產出趨勢分析 |

### 3. Changelog Generator（變更日誌生成器）

| 欄位 | 內容 |
|------|------|
| **名稱** | changelog-generator |
| **最佳用途** | 從 git commits 自動建立使用者導向的變更日誌 |
| **流程** | 讀取 git log → 分類 commits（feature/fix/breaking）→ 產出格式化 CHANGELOG |
| **實用場景** | 版本發佈前、Sprint 結束、需要向非技術人員溝通變更 |
| **範例** | 「產出 v2.3.0 的變更日誌」→ 自動分析 50 個 commits → 產出含 Features、Bug Fixes、Breaking Changes 的 CHANGELOG.md |

### 4. prompt-engineering（提示工程）

| 欄位 | 內容 |
|------|------|
| **名稱** | prompt-engineering |
| **最佳用途** | 套用經典提示工程技術優化 AI 互動品質 |
| **流程** | 分析當前提示 → 識別改進空間 → 套用技術（CoT, Few-shot, Self-consistency 等）→ 測試效果 |
| **實用場景** | 開發 AI 應用、優化 LLM 輸出品質、設計 system prompt |
| **範例** | 「優化我的客服機器人 prompt」→ 分析現有 prompt → 加入 Chain-of-Thought 推理 + few-shot 範例 → 回答準確率提升 |

### 5. root-cause-tracing（根因追蹤）

| 欄位 | 內容 |
|------|------|
| **名稱** | root-cause-tracing |
| **最佳用途** | 將執行錯誤追蹤到最原始的觸發因素 |
| **流程** | 收集錯誤資訊 → 追蹤 call stack → 分析數據流 → 找到根因 → 產出診斷報告 |
| **實用場景** | 生產環境事故分析、難以重現的 bug、連鎖錯誤診斷 |
| **範例** | 「追蹤為什麼 cron job 每週三凌晨失敗」→ 追蹤 log → 發現 DB 連線池耗盡 → 根因是週二晚的批次報表未釋放連線 |

### 6. software-architecture（軟體架構）

| 欄位 | 內容 |
|------|------|
| **名稱** | software-architecture |
| **最佳用途** | 實現設計模式與 SOLID 原則的架構指導 |
| **流程** | 分析現有架構 → 識別違反 SOLID 的地方 → 建議適當的設計模式 → 提供重構路徑 |
| **實用場景** | 新專案架構設計、重構決策、技術債評估 |
| **範例** | 「評估我的 API 層架構」→ 發現 controller 直接操作 DB（違反 SRP）→ 建議引入 Repository Pattern + Service Layer |

### 7. kaizen（持續改進）

| 欄位 | 內容 |
|------|------|
| **名稱** | kaizen |
| **最佳用途** | 應用持續改進方法論到程式碼與流程 |
| **流程** | 觀察現狀 → 識別浪費（Muda）→ 提出小幅改進 → 實施 → 驗證效果 → 持續迭代 |
| **實用場景** | 日常開發流程優化、技術債漸進清理、團隊效率提升 |
| **範例** | 「改進我們的 CI/CD 流程」→ 分析：build 耗時 12 分鐘 → 發現未快取依賴 + 序列化測試 → 改進後降至 4 分鐘 |

### 8. Composio Connect（SaaS 自動化連接器）

| 欄位 | 內容 |
|------|------|
| **名稱** | connect（Composio） |
| **最佳用途** | 連接 Claude 至 1000+ SaaS 應用執行真實動作 |
| **流程** | `/connect-apps:setup` → 提供 API key → 選擇要連接的應用 → Claude 直接操作外部服務 |
| **實用場景** | 跨應用自動化（Slack 通知 + Jira 建票 + Gmail 發信）、CRM 資料同步、社群媒體管理 |
| **範例** | 「當 GitHub PR 被 merge 後，在 Slack #releases 發通知並更新 Jira ticket 狀態」→ Claude 自動串接三個服務完成 |

---

## 六、與其他框架的定位比較

| 面向 | awesome-claude-skills | Superpowers | gstack | autoresearch |
|------|----------------------|-------------|--------|-------------|
| **性質** | 精選集合（聚合器） | 開發紀律框架 | 虛擬工程團隊 | 自主研究框架 |
| **維護者** | ComposioHQ（社群） | Jesse Vincent | Garry Tan | Andrej Karpathy |
| **Skills 數** | 60+ 獨立 + 800+ 整合 | 14 | 28 | 方法論（非 Skills） |
| **獨有價值** | 廣度最大、SaaS 整合 | TDD 紀律 | 產品策略 | 自主迭代 |
| **安全性** | ⚠️ 需逐一審查 | ✅ 較安全 | ✅ 較安全 | ✅ 較安全 |
| **適合** | 想要一站式瀏覽各種 skill 的使用者 | 重視工程品質 | 全端產品開發 | ML 研究 |

---

## 七、安全性總結與最終建議

### 安全性評級

| 來源 | 安全性 | 建議 |
|------|--------|------|
| **Anthropic 官方 Skills** | ✅✅✅ 最安全 | 優先使用 |
| **知名作者單一 repo**（Superpowers, gstack） | ✅✅ 較安全 | 建議使用，仍需審查 |
| **awesome-claude-skills 精選** | ⚠️ 需審查 | 逐一審查 SKILL.md 後使用 |
| **未知來源的 Skills** | ❌ 高風險 | 避免使用 |

### 最終建議

1. **有官方 Plugin 對應的 skill** → 直接用 Plugin（本清單約 40% 有對應）
2. **無 Plugin 但來自知名作者** → 審查後安裝 Skill
3. **Composio 整合** → 適合跨 SaaS 自動化需求，但注意 API key 權限最小化
4. **此清單最大價值** → 作為「發現工具」瀏覽有哪些 skill 存在，而非直接安裝來源

---

*最後更新：2026-03-24*

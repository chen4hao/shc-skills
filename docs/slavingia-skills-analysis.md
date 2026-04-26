# slavingia/skills — Minimalist Entrepreneur Skills 分析報告

> 分析日期：2026-03-25
> 來源：[github.com/slavingia/skills](https://github.com/slavingia/skills)
> 作者：Sahil Lavingia（Gumroad 創辦人，《The Minimalist Entrepreneur》作者）

---

## 一、概述

共 **9 個 Skills**，全部為純 Markdown prompt，無任何可執行程式碼。
安裝方式為 **Claude Code Plugin**（`.claude-plugin/plugin.json`），對應書本章節依序為：
社群 → 驗證 → 建造 → 銷售 → 定價 → 行銷 → 成長 → 文化 → 審視。

---

## 二、完整 Skills 清單

| # | Skill | 指令 | 用途 |
|---|-------|------|------|
| 1 | find-community | `/find-community` | 識別和評估適合建立事業的社群 |
| 2 | validate-idea | `/validate-idea` | 用極簡創業框架驗證商業點子（透過銷售驗證，非建造） |
| 3 | mvp | `/mvp` | 建立最小可行產品：手動 → 流程化 → 產品化 |
| 4 | first-customers | `/first-customers` | 找到前 100 位客戶（同心圓銷售法） |
| 5 | pricing | `/pricing` | 定價策略（成本定價 vs 價值定價、分層定價） |
| 6 | marketing-plan | `/marketing-plan` | 內容行銷計畫（教育 → 激勵 → 娛樂） |
| 7 | grow-sustainably | `/grow-sustainably` | 評估可持續成長（獲利、成本控制、避免倦怠） |
| 8 | company-values | `/company-values` | 定義公司價值觀與文化（3-5 條） |
| 9 | minimalist-review | `/minimalist-review` | 以 8 大極簡創業原則審視任何商業決策 |

---

## 三、安全性評估

| 項目 | 結果 |
|------|------|
| 可執行程式碼 | ❌ 完全沒有（純 Markdown） |
| 外部 API 呼叫 | ❌ 無 |
| 檔案系統操作 | ❌ 無（不建立/修改/刪除檔案） |
| 資料外洩風險 | ❌ 無（不傳送資料到外部服務） |
| 惡意 prompt injection | ❌ 未發現 |
| **風險等級** | **🟢 極低 — 安全可用** |

---

## 四、Plugin vs Skill 安裝方式比較

| 比較項目 | Claude Code Plugin | Vercel Skills CLI |
|---------|-------------------|-------------------|
| 安裝方式 | `git clone` 到 `~/.claude/plugins/` | `npx skills add repo -g` |
| 相容性 | 僅 Claude Code | 40+ AI CLI agents |
| 更新方式 | `git pull` 手動更新 | `npx skills update` |
| 解除安裝 | 手動刪除目錄 | `npx skills remove <name>` |
| 生態系廣度 | Claude Code 專屬 | 跨平台（Codex、Gemini、Kiro 等） |
| **建議** | 若只用 Claude Code 可直接裝 | **跨 agent 使用首選** |

> **結論**：若你只使用 Claude Code，兩種方式皆可；若同時使用多個 AI agent，Vercel Skills CLI 較佳。

---

## 五、對應替代工具（Plugin / MCP / 外部服務）

| 類別 | Skill 適合度 | MCP/工具適合度 | 最佳替代方案 | 建議策略 |
|------|:----------:|:------------:|------------|---------|
| 行銷/文案 | ⭐⭐⭐ | ⭐ | `coreyhaines31/marketingskills@copywriting` (46K installs) | **Skill 為主** |
| 產品發布 | ⭐⭐⭐ | ⭐ | `inferen-sh/skills@product-hunt-launch` (7.8K installs) | **Skill 為主** |
| 商業模型 | ⭐⭐⭐ | ⭐ | `scientiacapital/skills@business-model-canvas` | **Skill 為主** |
| Stripe 支付 | ⭐⭐ | ⭐⭐⭐ | Stripe 官方 MCP Server (`mcp.stripe.com`) | MCP + Skill 互補 |
| Email 行銷 | ⭐⭐ | ⭐⭐⭐ | MailerLite / Brevo / Klaviyo MCP Server | MCP + Skill 互補 |
| 客戶回饋 | ⭐⭐ | ⭐⭐ | `softaworks/agent-toolkit@feedback-mastery` (3.4K installs) | 兩者互補 |
| Landing Page | ⭐ | ⭐⭐⭐ | v0.dev / Bolt.new / Lovable | **外部工具為主** |
| MVP 建置 | ⭐ | ⭐⭐⭐ | Bolt.new / Lovable / Replit Agent | **外部工具為主** |

---

## 六、最推薦 Skills 速查表

以下 5 個 Skill 最適合以 prompt 方式使用（不需外部 API 即可發揮最大價值）：

| 名稱 | 最佳用途 | 流程 | 實用場景 | 範例 |
|------|---------|------|---------|------|
| **validate-idea** | 快速驗證商業點子是否值得投入 | 定義問題 → 手動解決 → 確認付費意願 → 回答四大問題 | 創業初期、side project 啟動前 | 「我想做一個幫自由工作者追蹤發票的工具，幫我驗證」 |
| **marketing-plan** | 零預算內容行銷規劃 | 定義受眾 → 三層內容策略（教育/激勵/娛樂）→ 排程 | 產品上線後需要曝光、預算有限 | 「我的 SaaS 剛上線，幫我規劃第一個月的行銷計畫」 |
| **pricing** | 為產品/服務制定合理價格 | 分析成本 → 評估價值 → 設計分層 → 計算財務獨立數學 | 定價困難、不確定要收多少錢 | 「我的線上課程該定價多少？目標群是初級開發者」 |
| **minimalist-review** | 用極簡原則審視任何商業決策 | 逐一檢查 8 大原則 → 產出決策矩陣 | 面臨擴張/募資/轉型等重大決策 | 「我正考慮接受天使投資，幫我用極簡原則分析」 |
| **first-customers** | 系統性找到第一批付費客戶 | 列出親友圈 → 社群觸及 → 冷信模板 → 追蹤轉換 | 產品做好了但不知道怎麼賣 | 「我做了一個 Notion 模板，如何找到前 50 個買家？」 |

---

## 七、核心洞察

> **Skill（Markdown prompt）最適合純策略 / 文案 / 框架思考任務。**
> 一旦涉及外部 API 操作或程式碼生成，MCP Server 或 app builder 工具會大幅超越。
> **最佳實踐：Skill 用於「想清楚要做什麼」，MCP/工具用於「實際執行」。**

---

*本報告由 Claude Code 自動生成*

# garrytan/gstack — Garry Tan (YC CEO) 虛擬開發團隊 Skills 分析報告

> 分析日期：2026-03-25
> 來源：[github.com/garrytan/gstack](https://github.com/garrytan/gstack)
> 作者：Garry Tan（Y Combinator 總裁暨 CEO）
> ⭐ 45,516 | 🍴 5,706 | 授權：MIT

---

## 一、概述

gstack **不是**創業/YC 諮詢工具——它是一套**虛擬軟體開發團隊**，將 Claude Code 變成包含 CEO、工程經理、設計師、QA、安全長、發布工程師等角色的完整開發流程系統。

核心哲學："Boil the Lake"（把湖煮沸）——AI 使完整性的邊際成本趨近於零，永遠選最完整的方案。Garry Tan 宣稱用此工具 50 天內每週產出 10,000 行程式碼和 100 個 PR。

共 **28 個 Skills**，分五大階段：計劃 → 建置 → 測試 → 發布 → 安全。

---

## 二、完整 Skills 清單

### 計劃階段（Think/Plan）— 6 個

| # | Skill | 角色 | 功能 |
|---|-------|------|------|
| 1 | `/office-hours` | YC Office Hours | 六個強制提問重新定義產品方向，產出設計文件 |
| 2 | `/plan-ceo-review` | CEO / Founder | 重新思考問題、找到 10 星級產品。四種模式：Expansion / Selective / Hold / Reduction |
| 3 | `/plan-eng-review` | 工程經理 | 鎖定架構、資料流、ASCII 圖、邊界案例、測試計畫 |
| 4 | `/plan-design-review` | 資深設計師 | 設計各維度評分 0-10，AI 垃圾偵測，每個決策互動確認 |
| 5 | `/design-consultation` | 設計夥伴 | 從零建立完整設計系統，研究市場、提出創意風險 |
| 6 | `/autoplan` | 審查管線 | 一鍵自動跑 CEO + 設計 + 工程審查，6 個決策原則自動回答 |

### 建置與審查（Build/Review）— 4 個

| # | Skill | 角色 | 功能 |
|---|-------|------|------|
| 7 | `/review` | Staff Engineer | 找到通過 CI 但在生產環境會爆的 Bug，自動修復明顯問題 |
| 8 | `/investigate` | 除錯器 | 系統性根因除錯，鐵律：先調查才修復，3 次失敗即停止 |
| 9 | `/design-review` | 會寫 Code 的設計師 | 同 plan-design-review 審核標準，但直接修復問題 |
| 10 | `/codex` | 第二意見 | 呼叫 OpenAI Codex CLI 做獨立 code review（review / adversarial / open 三模式） |

### 測試（Test）— 6 個

| # | Skill | 角色 | 功能 |
|---|-------|------|------|
| 11 | `/qa` | QA Lead | 真實瀏覽器測試 → 找 Bug → 修復 → 回歸測試 |
| 12 | `/qa-only` | QA Reporter | 同 /qa 方法論，但只產報告不改 code |
| 13 | `/browse` | QA 工程師 | 真實 Chromium 瀏覽器，真實點擊/截圖，每指令約 100ms |
| 14 | `/benchmark` | 效能工程師 | 頁面載入時間、Core Web Vitals、資源大小基準測試 |
| 15 | `/canary` | SRE | 部署後監控迴圈（console 錯誤、效能退化、頁面故障） |
| 16 | `/cso` | 資安長 | OWASP Top 10 + STRIDE 威脅模型，8/10+ 信心門檻，17 種誤判排除 |

### 發布（Ship）— 4 個

| # | Skill | 角色 | 功能 |
|---|-------|------|------|
| 17 | `/ship` | 發布工程師 | Sync main → 跑測試 → 審計覆蓋率 → 推送 → 開 PR |
| 18 | `/land-and-deploy` | 發布工程師 | 合併 PR → 等 CI 和部署 → 驗證生產環境健康 |
| 19 | `/document-release` | 技術寫手 | 更新所有專案文件以匹配發布內容 |
| 20 | `/retro` | 工程經理 | 團隊感知週回顧，支援 `/retro global` 跨專案 |

### 安全工具（Safety/Power Tools）— 8 個

| # | Skill | 功能 |
|---|-------|------|
| 21 | `/careful` | 破壞性命令前警告（rm -rf、DROP TABLE、force-push） |
| 22 | `/freeze` | 限制檔案編輯範圍到單一目錄 |
| 23 | `/guard` | `/careful` + `/freeze` 合一，最大安全模式 |
| 24 | `/unfreeze` | 解除 `/freeze` 限制 |
| 25 | `/setup-browser-cookies` | 從真實瀏覽器匯入 cookies 到 headless session |
| 26 | `/setup-deploy` | 一次性部署設定偵測 |
| 27 | `/gstack-upgrade` | 自我更新 |
| 28 | `/codex` | OpenAI Codex CLI 第二意見整合 |

---

## 三、安全性評估

### 🟡 風險等級：中

**與前幾份分析的根本差異：gstack 不是純 Markdown，包含真實可執行程式碼。**

| 項目 | 風險 | 說明 |
|------|------|------|
| 編譯二進位檔 | ⚠️ 中 | `browse/dist/browse` 是 bun compile 的 Chromium 控制器 |
| npm/bun 依賴 | ⚠️ 中 | playwright ^1.58.2、diff、@anthropic-ai/sdk |
| Shell 腳本大量執行 | ⚠️ 中 | `bin/` 下 10+ 個 bash 腳本，每個 SKILL.md 前置執行 shell 命令 |
| Supabase 遙測後端 | ⚠️ 低-中 | 資料同步到 `frugpmstpnojnhfyimgv.supabase.co`（**預設關閉**，需明確同意） |
| `curl \| bash` 安裝 | ⚠️ 中 | setup 腳本在 bun 未安裝時建議 `curl -fsSL https://bun.sh/install \| bash` |
| 瀏覽器 Cookie 匯入 | ⚠️ 中 | `/setup-browser-cookies` 可從 Chrome/Arc/Brave/Edge 匯入登入狀態 |
| OpenAI 資料傳送 | ⚠️ 中 | `/codex` 會將程式碼傳送給 OpenAI Codex CLI |
| 首次使用開啟 URL | ⚠️ 低 | 首次執行嘗試 `open https://garryslist.org/posts/boil-the-ocean` |
| SSRF 防護 | ✅ 正面 | URL 驗證封鎖雲端 metadata endpoint、DNS rebinding |
| 遙測欄位過濾 | ✅ 正面 | 不傳送程式碼、檔案路徑、repo 名稱 |
| 資料外洩模式 | ❌ 未發現 |
| 惡意指令 | ❌ 未發現 |

> **⚠️ 與 shc-skills CLAUDE.md 的衝突**：
> - `curl | bash` 安裝模式 → 你的 CLAUDE.md 明確禁止
> - `npm install -g` 可能性 → 你的 CLAUDE.md 明確禁止
> - bun 依賴 → 已安裝（相容）
> - 使用前建議仔細審查 `setup` 腳本內容

---

## 四、Plugin vs Skill 安裝方式比較

| 比較項目 | gstack（git clone + setup） | Vercel Skills CLI | Claude Code Plugin |
|---------|---------------------------|-------------------|-------------------|
| 安裝複雜度 | **高**（clone + bun build） | 低（npx skills add） | 低（marketplace） |
| 依賴安裝 | ⚠️ playwright + bun compile | 無 | 視 plugin 而定 |
| 瀏覽器功能 | ✅ 內建 headless Chromium | ❌ | 需額外 MCP |
| 跨 agent 支援 | ✅ Claude/Codex/Gemini/Cursor/Kiro | ✅ 42 個 agent | ❌ 僅 Claude |
| 更新方式 | `/gstack-upgrade` 自動 | `npx skills update` | Marketplace 自動 |
| 安全管控 | 自帶 `/careful` `/freeze` `/guard` | Audit API | Claude 權限系統 |
| **建議** | **重度開發者、需要完整流程管線** | 輕量知識型 skill | 需嚴格權限管控 |

> **結論**：gstack 適合**全職軟體開發者**需要完整 CI/CD-like 流程管線的場景。若只需單一功能（如 code review），用 Skills CLI 安裝輕量 skill 更合適。

---

## 五、對應替代工具（競品/互補）

| gstack Skill | 最強替代方案 | 類型 | 差異說明 |
|-------------|-------------|------|---------|
| /review | **obra/superpowers** (106K⭐) | Plugin | Superpowers 強調 TDD-first，gstack 強調生產環境 bug |
| /qa + /browse | **Playwright MCP Server** | MCP | gstack 內建完整 Chromium daemon，MCP 更靈活 |
| /ship | **shc-commit-push-pr** | Skill | shc 更輕量，gstack 含測試+覆蓋率審計 |
| /cso | **Trail of Bits skills** | Skill | Trail of Bits 專業安全公司，更深入 |
| /plan-ceo-review | **slavingia/skills@validate-idea** | Skill | 不同切角：gstack 偏技術產品決策，slavingia 偏商業驗證 |
| /benchmark | **Lighthouse CI** / **web-vitals** | CLI | gstack 整合度高，獨立工具更精確 |
| /codex | **GitHub Copilot** | VS Code | gstack 用 Codex 做第二意見，Copilot 是常駐助手 |
| /autoplan | （無直接競品） | — | gstack 獨創：一鍵串聯 CEO+設計+工程三層審查 |
| /canary | **Datadog / Sentry** | SaaS | 專業監控工具更完整，gstack 是輕量版 |

---

## 六、最推薦 Skills 速查表

以下 8 個 Skill 最具獨特價值且難以被其他工具替代：

| 名稱 | 最佳用途 | 流程 | 實用場景 | 範例 |
|------|---------|------|---------|------|
| **`/autoplan`** | 一鍵跑完 CEO + 設計 + 工程三層審查 | 自動串聯三個 review → 用 6 個決策原則回答中間問題 → 產出完整計畫 | 新功能開發前的完整規劃、大型重構前評估 | 「幫我規劃一個即時通知系統」→ 自動完成商業價值/設計/架構三層審查 |
| **`/review`** | 找出通過 CI 但生產環境會爆的 Bug | 逐檔 diff 審查 → 標記嚴重度 → 自動修復明顯問題 → 產出報告 | PR review、合併前最後檢查 | 「review 我的最新 PR」→ 找到 race condition 和未處理的 edge case |
| **`/qa`** | 真實瀏覽器端對端測試 + 自動修復 | 啟動 Chromium → 遍歷功能 → 截圖記錄 → 找 Bug → 修復 → 回歸測試 | 上線前完整 QA、UI 回歸測試 | 「QA 我的登入流程」→ 用真實瀏覽器測試，找到 CSS 破版並修復 |
| **`/cso`** | OWASP Top 10 + STRIDE 安全稽核 | 掃描程式碼 → STRIDE 威脅模型 → 8/10+ 信心門檻過濾 → 17 種誤判排除 | 上線前安全審查、處理敏感資料的功能 | 「安全審查我的 API 認證模組」→ 找到 JWT 驗證漏洞 |
| **`/investigate`** | 系統性根因除錯 | 收集證據 → 形成假設 → 驗證 → 鐵律：先調查才修復，3 次失敗即停止 | 神秘 bug、間歇性問題、生產環境 incident | 「使用者回報頁面偶爾白屏」→ 系統性追蹤到 race condition |
| **`/ship`** | 自動化發布流程 | sync main → 跑測試 → 審計覆蓋率 → 推送 → 開 PR | 日常 code 發布 | 「ship 這個 feature branch」→ 自動完成測試、推送、PR 建立 |
| **`/guard`** | 最大安全模式（careful + freeze 合一） | 設定檔案編輯範圍 + 破壞性命令攔截 | 操作生產環境、修改核心模組 | 「/guard src/auth/」→ 限制只能改 auth 目錄，rm/force-push 前警告 |
| **`/office-hours`** | YC 風格的產品方向質詢 | 六個強制提問 → 挑戰假設 → 產出設計文件 | 產品方向迷茫、功能優先排序困難 | 「我不確定下一步該做什麼功能」→ 六個深度提問幫你釐清方向 |

---

## 七、與 shc-skills 的互補關係

| 面向 | shc-skills | gstack | 關係 |
|------|-----------|--------|------|
| **性質** | 純 Markdown prompt | Markdown + 編譯二進位 + Shell + 遙測後端 | 根本不同 |
| **安裝複雜度** | `npx skills add`（零依賴） | `git clone` + `bun build`（需 playwright） | shc 更輕量 |
| **Code Review** | ✅ shc-review（輕量） | ✅ /review（重量級，含自動修復） | 互補 |
| **除錯** | ✅ shc-debug（通用） | ✅ /investigate（結構化根因分析） | 互補 |
| **測試** | ✅ shc-test（通用） | ✅ /qa（真實瀏覽器 E2E） | 互補 |
| **Git/PR** | ✅ shc-commit-push-pr | ✅ /ship + /land-and-deploy | 重疊但深度不同 |
| **安全** | ❌ | ✅ /cso（OWASP + STRIDE） | gstack 獨有 |
| **設計審查** | ❌ | ✅ /design-review + /design-consultation | gstack 獨有 |
| **瀏覽器測試** | ❌ | ✅ /browse + /qa（內建 Chromium） | gstack 獨有 |
| **產品方向** | ❌ | ✅ /office-hours + /plan-ceo-review | gstack 獨有 |
| **繁體中文** | ✅ | ❌ | shc 獨有 |
| **知識萃取** | ✅ shc-distill | ❌ | shc 獨有 |
| **程式碼解釋** | ✅ shc-explain | ❌ | shc 獨有 |
| **技術債掃描** | ✅ shc-techdebt | ❌ | shc 獨有 |

> **最佳策略**：shc-skills 作為**輕量日常 workflow 基底**，gstack 在需要**重量級審查管線**（安全稽核、E2E QA、設計審查、自動化發布）時啟用。兩者互補程度高。

---

## 八、核心洞察

> 1. **gstack 是目前最「重量級」的 skill 集合**——內建 Chromium daemon、遙測後端、編譯二進位，遠非純 Markdown prompt
> 2. **`/autoplan` 是殺手級功能**——一鍵串聯 CEO + 設計 + 工程三層審查，目前無直接競品
> 3. **安全性可接受但需審慎**——遙測預設關閉、SSRF 防護完善，但 `curl | bash` 安裝和 cookie 匯入需注意
> 4. **最大競品 obra/superpowers（106K⭐）取向不同**——superpowers 強調 TDD 流程，gstack 強調角色分工與完整性
> 5. **適合全職軟體開發者**，不適合只需輕量輔助的場景（用 shc-skills 或 Vercel Skills 更合適）

---

*本報告由 Claude Code 自動生成*

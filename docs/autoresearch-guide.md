# Autoresearch — Karpathy 的自主 AI 研究框架完整指南

> **來源：** [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
> **作者：** Andrej Karpathy（前 Tesla AI 總監、OpenAI 創始成員、史丹佛 CS231n 講師）
> **類型：** 自主 AI 研究框架 + 方法論（非傳統 Skills 集合）
> **授權：** MIT 開源

---

## 一、框架簡介

**autoresearch** 是 Andrej Karpathy 開發的實驗性框架，讓 AI agent 在單 GPU 上**自主進行深度學習研究**。agent 會自動修改訓練程式碼、執行實驗、評估改進，並持續迭代優化——完全無需人工干涉。

### 這不是傳統的 Skills 集合

與 Superpowers、gstack 不同，autoresearch **不是** Vercel Skills CLI 格式的 SKILL.md 集合。它是一個**完整的自主研究 agent 框架**，核心是一份 `program.md` 指令檔，定義了 agent 的完整行為協議。

然而，autoresearch 的**方法論**（自主迭代、固定時間預算、結構化結果追蹤）已被社群廣泛改編為各種 Claude Code skills，成為影響力最大的 AI agent 工作模式之一。

### Karpathy 的工作流程轉變

> 「從 2025 年 11 月的 80% 手工編碼，轉變為 80% AI agent 編碼。這是我約 20 年編程生涯中**最大的基礎工作流程改變**。」

首周即獲得 **42,000+ GitHub stars**。

---

## 二、核心架構與元件

### 檔案結構

| 檔案 | 角色 | 說明 |
|------|------|------|
| `program.md` | Agent 指令 | 定義完整行為協議、實驗循環、約束規則 |
| `train.py` | 可修改目標 | Agent 唯一可編輯的訓練腳本（GPT 模型） |
| `prepare.py` | 固定配置 | 資料準備與評估工具（禁止修改） |
| `results.tsv` | 結果追蹤 | 結構化記錄每次實驗（commit, val_bpb, memory, status, description） |
| `analysis.ipynb` | 分析面板 | Jupyter 筆記本視覺化實驗進度 |

### 自主實驗循環（核心流程）

```
┌─────────────────────────────────────┐
│  1. 查看 git 狀態                     │
│  2. 修改 train.py（提出假設並實作）    │
│  3. git commit                       │
│  4. 執行 uv run train.py             │
│  5. 提取結果（val_bpb, peak_vram）    │
│  6. 記錄到 results.tsv               │
│  7. 若改進 → 保留；否則 git reset     │
│  8. 回到步驟 1（永遠持續）             │
└─────────────────────────────────────┘
```

### 關鍵約束

| 約束 | 規則 |
|------|------|
| 修改範圍 | 僅限 `train.py` |
| 時間預算 | 每次實驗 5 分鐘牆鐘時間 |
| 禁止項 | 修改 `prepare.py`、新增依賴、修改評估函式 |
| 優化目標 | 最小化 `val_bpb`（驗證位元/位元組） |
| 超時處理 | 超過 10 分鐘視為失敗 |
| 設計原則 | 簡潔性優於複雜度 |

---

## 三、安裝方式比較：Plugin vs Skill vs 原始框架

### 三種取得方式

| 方式 | 來源 | 安裝指令 |
|------|------|----------|
| **原始框架** | [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | `git clone` + `uv sync` + `uv run prepare.py` |
| **社群 Plugin** | [forrestchang/andrej-karpathy-skills](https://www.claudepluginhub.com/plugins/forrestchang-andrej-karpathy-skills) | `claude plugin install andrej-karpathy-skills` |
| **社群 Skill 改編** | 多個社群版本 | `npx skills add` 或 `git clone` |

### 詳細比較

| 比較項目 | 原始框架 | 社群 Plugin | 社群 Skill 改編 |
|---------|---------|-------------|----------------|
| **維護者** | Karpathy 本人 | Forrest Chang（第三方） | 各社群開發者 |
| **用途** | 自主 ML 研究（需 GPU） | Claude Code 開發 skills | 將方法論應用於日常開發 |
| **需要 GPU** | ✅ 是 | ❌ 否 | ❌ 否 |
| **自訂彈性** | 高（直接改 program.md） | 低 | 高 |
| **適合對象** | ML 研究者 | 一般 Claude Code 使用者 | 想自訂方法論的進階使用者 |
| **平台支援** | 任何支援 Claude/Codex 的 agent | 僅 Claude Code | 多平台 |

### 建議

- **ML 研究者** → 直接用原始框架，在 GPU 上跑自主實驗
- **一般開發者想快速體驗** → 社群 Plugin（一行安裝）
- **想深入應用 autoresearch 方法論** → 參考社群改編版，自訂適合自己的 skill

---

## 四、Autoresearch 方法論衍生的實用 Skills

雖然原始 autoresearch 是 ML 研究框架，但其核心方法論已被社群改編為多種實用 skills：

### 核心方法論提煉

autoresearch 的精髓可歸納為 **5 個可遷移的模式**：

| 模式 | 原始用途 | 通用化應用 |
|------|---------|-----------|
| **自主迭代循環** | 自動修改 train.py 並測試 | 任何需要反覆嘗試的最佳化任務 |
| **固定時間預算** | 5 分鐘/實驗 | 限制 agent 不會無限探索 |
| **結構化結果追蹤** | results.tsv | 用 TSV/JSON 記錄每次嘗試 |
| **保留/回退機制** | git commit + git reset | 改進就保留，否則回退 |
| **單一修改範圍** | 僅限 train.py | 限制 agent 只動指定檔案 |

---

## 五、最推薦的 Skills 速查表

以下整理 autoresearch 方法論中最值得採用的 **6 個核心技能模式**：

### 1. 自主實驗循環（Autonomous Experiment Loop）

| 欄位 | 內容 |
|------|------|
| **名稱** | autonomous-experiment-loop |
| **最佳用途** | 讓 agent 自主嘗試多種方案，無需人工逐一指導 |
| **流程** | 提出假設 → 實作修改 → git commit → 執行測試 → 評估結果 → 改進則保留/否則回退 → 重複 |
| **實用場景** | 性能最佳化、演算法調參、CSS 樣式迭代、API 回應優化 |
| **範例** | 「最佳化這個 SQL 查詢的效能」→ agent 嘗試加索引（提升 20%，保留）→ 嘗試改 JOIN 順序（無改善，回退）→ 嘗試子查詢改寫（再提升 15%，保留）|

### 2. 固定時間預算（Time-Boxed Experimentation）

| 欄位 | 內容 |
|------|------|
| **名稱** | time-boxed-experimentation |
| **最佳用途** | 防止 agent 無限探索，確保在有限時間內產出結果 |
| **流程** | 設定時間上限（如 5 分鐘/實驗）→ 超時視為失敗 → 記錄結果 → 嘗試不同方向 |
| **實用場景** | 任何最佳化任務、探索性開發、不確定最佳解的問題 |
| **範例** | 「用 5 分鐘嘗試改善首頁載入速度」→ agent 在時間內嘗試 lazy loading、圖片壓縮、code splitting → 超時則停止並報告最佳結果 |

### 3. 結構化結果追蹤（Structured Result Tracking）

| 欄位 | 內容 |
|------|------|
| **名稱** | structured-result-tracking |
| **最佳用途** | 以結構化格式記錄每次嘗試，方便比較和分析 |
| **流程** | 定義指標欄位 → 每次實驗後記錄到 TSV/JSON → 標記保留/捨棄/失敗 → 可視覺化分析 |
| **實用場景** | A/B 測試、性能基準、多方案比較、長期追蹤 |
| **範例** | 記錄格式：`commit | 回應時間ms | 記憶體MB | 狀態 | 描述` → 10 次實驗後一目了然哪些改動有效 |

### 4. 保留/回退機制（Keep/Revert Protocol）

| 欄位 | 內容 |
|------|------|
| **名稱** | keep-revert-protocol |
| **最佳用途** | 確保只保留有效改進，失敗嘗試不會污染 codebase |
| **流程** | git commit 每次修改 → 執行驗證 → 改進則保留 → 未改進則 `git reset` → 確保乾淨基線 |
| **實用場景** | 重構、性能最佳化、任何不確定結果的修改 |
| **範例** | 嘗試將 React 元件改為 memo → 測試顯示渲染時間無變化 → `git reset` 回退 → 嘗試 useMemo 優化計算 → 渲染時間降 30% → 保留 |

### 5. 單一修改範圍（Single-File Constraint）

| 欄位 | 內容 |
|------|------|
| **名稱** | single-file-constraint |
| **最佳用途** | 限制 agent 修改範圍，避免失控散射式修改 |
| **流程** | 明確指定可修改檔案 → agent 只在範圍內操作 → 禁止新增依賴或動其他檔案 |
| **實用場景** | 精準最佳化特定模組、安全地讓 agent 自主操作、降低回退成本 |
| **範例** | 「只修改 `src/utils/parser.ts`，最佳化解析效能」→ agent 在限定範圍內嘗試多種演算法，不會意外動到其他檔案 |

### 6. 自主研究代理（Autonomous Research Agent）

| 欄位 | 內容 |
|------|------|
| **名稱** | autonomous-research-agent |
| **最佳用途** | 讓 agent 在你睡覺/開會時自主進行 ML 研究最佳化 |
| **流程** | 設定 program.md 指令 → 指定目標指標 → 啟動 agent → 自動迭代（~100 次/晚）→ 醒來看 results.tsv |
| **實用場景** | ML 模型調參、訓練腳本最佳化、神經網路架構搜尋 |
| **範例** | 「最佳化 GPT 訓練的 val_bpb」→ agent 整夜自動嘗試：調整 attention head 數量、改 activation function、修改 learning rate schedule → 早上查看 results.tsv 發現 val_bpb 從 1.42 降到 1.31 |

---

## 六、典型工作流程

### ML 研究場景（原始用途）

```
uv sync && uv run prepare.py     ← 準備環境與資料
    ↓
啟動 Claude Code / Codex
    ↓
載入 program.md 作為 agent 指令
    ↓
┌─────────────────────────┐
│  自主實驗循環（整夜運行）  │
│  修改 → 測試 → 評估       │
│  保留 or 回退              │
│  ~100 次實驗/晚           │
└─────────────────────────┘
    ↓
查看 results.tsv + analysis.ipynb
    ↓
挑選最佳結果繼續發展
```

### 通用開發場景（方法論遷移）

```
定義目標指標（回應時間、覆蓋率、bundle size...）
    ↓
設定修改範圍（指定可編輯的檔案）
    ↓
設定時間預算（每次嘗試 N 分鐘）
    ↓
agent 自主迭代
    ├─ 嘗試方案 A → 改進 → 保留
    ├─ 嘗試方案 B → 無改善 → 回退
    └─ 嘗試方案 C → 改進 → 保留
    ↓
查看結構化結果 → 挑選最佳方案
```

---

## 七、與其他框架的定位比較

| 面向 | autoresearch | Superpowers | gstack |
|------|-------------|-------------|--------|
| **定位** | 自主 ML 研究 + 方法論 | 工程紀律框架 | 虛擬工程團隊 |
| **類型** | 研究框架（非 Skills 集合） | Skills 集合 | Skills 集合 |
| **核心特色** | 自主迭代、固定預算、結果追蹤 | TDD、系統性除錯 | CEO/設計/安全審查 |
| **需要 GPU** | ✅（原始用途） | ❌ | ❌ |
| **適合** | ML 研究者、最佳化狂人 | 重視測試紀律的團隊 | 產品導向的全端開發 |
| **Plugin 版** | ✅ 第三方社群版 | ✅ 官方 | ❌ 無 |
| **獨有價值** | 「睡覺時讓 AI 做研究」的範式 | 強制 TDD 紀律 | 產品策略 + 完整生命週期 |

---

## 八、社群生態

| 專案 | 說明 |
|------|------|
| [forrestchang/andrej-karpathy-skills](https://www.claudepluginhub.com/plugins/forrestchang-andrej-karpathy-skills) | 社群 Plugin 版，一行安裝 |
| [uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch) | 將方法論擴展到行銷、銷售、研究等日常活動 |
| [wanshuiyin/Auto-Research-In-Sleep (ARIS)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | 輕量級 Markdown skill，支援跨模型審查 |
| [drivelineresearch/autoresearch-claude-code](https://github.com/drivelineresearch/autoresearch-claude-code) | Driveline Research 移植版 |

---

*最後更新：2026-03-24*

---
name: shc-techdebt
description: >
  技術債掃描。Use when the user wants to scan for technical debt, code smells,
  or quality issues in the codebase.
---

# 技術債掃描 (Tech Debt Scan)

**觸發條件**：使用者要求掃描技術債、code smell、或程式碼品質問題。
**關鍵字**：techdebt, 技術債, code smell, 掃描, scan for issues, code quality

## 流程

1. **重複程式碼**：找出高度相似或 copy-paste 的程式碼片段
2. **過度複雜**：找出巢狀過深、函式過長、圈複雜度過高的區塊
3. **命名問題**：變數、函式、檔案命名不清或不一致
4. **缺少測試**：核心功能缺少測試覆蓋
5. **過時依賴**：檢查 package.json / pyproject.toml 中可能有安全風險的舊版套件
6. **TODO/FIXME/HACK**：搜尋程式碼中遺留的標記

以表格形式輸出，按優先順序排列（🔴 高 / 🟡 中 / 🟢 低），並附上建議的修復方式。

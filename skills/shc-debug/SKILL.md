---
name: shc-debug
description: >
  除錯模式。Use when the user reports a bug, error, or unexpected behavior
  and wants systematic debugging help.
---

# 除錯模式 (Debug)

**觸發條件**：使用者回報 bug、錯誤、或非預期行為，需要系統性除錯協助。
**關鍵字**：debug, 除錯, bug, error, 為什麼會, 怎麼壞了, crash, exception, 不work, 不能用

## 流程

1. **重現問題**：確認問題的具體表現和錯誤訊息
2. **縮小範圍**：追蹤 call stack，定位到出問題的具體檔案和行數
3. **分析根因**：找出 root cause，而非只處理表面症狀
4. **提出修復方案**：說明修復方式和原因
5. **驗證修復**：執行相關測試或指令確認問題已解決
6. **預防措施**：建議是否需要加入測試或防護以避免復發

每一步都請先說明你的推理過程再行動。

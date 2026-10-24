# HANDOFF

接手文件：每個 session 一節，新的在最上面。日期用 ISO 8601。

---

## 2026-10-24（星期六）shc-distill：字幕翻譯指示修正與子代理分批上限

**結論**：翻譯子代理不再把回報句寫進字幕；超過 6 個子代理時改為每則訊息最多 6 個。兩項都已 commit 並 push。

**本 session 的 commit**（分支 `distill/sync-2026-04-26`）
- `ac00984` fix(split_batches)：刪除翻譯指示裡的回報條目數那一行
- `e6b89c3` docs(shc-distill)：`SKILL.md` 加分批上限，建立本檔
- `8652325` fix(split_batches)：stdout 提示改成 advisor 先發、Agent 每則最多 6 個

**沒做完的事**：無。

<details>
<summary><b>經過與裁決</b></summary>

1. 使用者要 distill Tim Ferriss #748（`9yd07qN_bSA`）。查到它是 2024-06 十週年合輯（`yRFEb8KJC2I`）的第三方重傳版，`infoAggr/Tim-Ferriss/2024-06-Pavel-Tsatsouline-and-Chris-Sommer.md` 已整理過，但筆記開頭列的 3 個字幕檔不存在。
   - 裁決：「停止 (Recommended)」
2. 使用者改要補字幕：「用 #748 補做舊筆記的三個字幕檔」。
   - 比對時間軸：#748 比原片早 16–18 秒，廣告也不同。
   - 裁決：「改用舊影片字幕 (Recommended)」
   - 結果：3 個字幕檔各 2278 條，修正 24 組英文誤聽。`Tony Fay`、`Stacy` 查不到正確拼法，保留原樣。
3. sample batch 1 的第 88 條變成「輸入條目數=88，輸出條目數=88，確認一致。」，第 86–87 條錯位一格。原因是 `split_batches.py` 的指示要求回報條目數。
   - 裁決：「改」→ `ac00984`
   - 新規則寫「原文最後一條」而非「第 {entry_count} 條」，因為第 2 批起字幕編號延續。
4. 一次發 26 個 Agent，17 個回 `Lock file is already being held`。每則 6 個補發後全部成功。
   - 裁決：「3」（`SKILL.md` 寫入分批上限 ＋ 建立本檔）→ `e6b89c3`
   - 提議時寫「每則最多 8 個」，寫入時改成驗證過的 6 個；8 個沒測過。
5. 裁決：「push & sync」
   - Push 成功（`5736016..ac00984`）。
   - Sync 沒有執行：`~/.agents/skills/shc-distill` 與 `~/.claude/skills/shc-distill` 都是指向本 repo 的 symlink，commit 後就生效。跑 `rsync --delete` 會寫回 repo 本身並刪掉 `__pycache__`。
6. `split_batches.py` 的 stdout 提示與「advisor 序列前置」、分批上限衝突。
   - 裁決：「1」（改提示文字）→ `8652325`
   - 改成：≤3 批先 advisor 單獨一則、再發全部 Agent；≥4 批先發 batch 1，advisor 單獨一則，驗證後其餘批次每則最多 6 個，stdout 算好分幾則。
   - `SKILL.md` 的門檻同步從「超過 10 個」改為「超過 6 個」，與腳本一致。
   - 測試：20 條樣本分 2 批、20 批兩種情況，提示文字與則數算式都正確。

</details>

<details>
<summary><b>給下一個接手者的注意事項</b></summary>

- `split_batches.py` 的 stdout 原本印「27 Agent + advisor() 同訊息並行」，和使用者的記憶規則「advisor 序列前置」衝突。裁決「1」後已改成：advisor 單獨一則先發、Agent 每則最多 6 個並算好分幾則。
- 子代理通知不附 output-file。翻譯記錄在 `~/.claude/projects/{專案}/{session}/subagents/agent-{name}-{id}.jsonl`，要 cp 改名成 `.output` 再給 `finalize_video_distill.py`。只複製本次批次的檔名（例如 `agent-azbatch*`），避免混入停掉的舊批次。

</details>

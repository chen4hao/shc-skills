# HANDOFF

接手文件：每個 session 一節，新的在最上面。日期用 ISO 8601。

---

## 2026-10-29（星期四）shc-distill：FunASR 修補 Whisper 幻覺區的三支腳本

**結論**：新增 3 支腳本。中文長課堂的 Whisper 字幕若卡成重複字，可以用 FunASR Paraformer 切段重轉後補回。腳本已 commit，push 與本檔一起進行。

**本 session 的 commit**（分支 `distill/sync-2026-04-26`）
- `420c17d` feat(shc-distill)：加入 `funasr_patch.py`、`hallu_scan.py`、`srt_to_paragraphs.py`
- `5f250a6` docs(handoff)：本節
- `23241a9` docs(shc-distill)：`SKILL.md` 在「STT 完成後字元頻次預檢」之後加入 FunASR 修補流程（裁決：「1」）

**沒做完的事**
- `funasr_patch.py` 在 commit 前改過兩處（`OUT_SUFFIX` 生效、說明文字）。改完只做了 `py_compile`，沒有完整重跑一次。
- 工作區有一個不是本 session 改的檔案：`skills/shc-distill/scripts/whisper_stt.py`（新增 `--condition-on-previous-text` 參數）。本 session 沒有 stage 它。

<details>
<summary><b>經過與裁決</b></summary>

1. 使用者要 distill Bilibili `BV19MGi6dEHC`（北大《價值投資課程》，7 P）。B 站回 HTTP 412（IP 風控），yt-dlp、API、帶 Chrome cookie、關沙箱都失敗。
   - 使用者提供本地 mp3：`~/aiDownload/【北京大学】经典《价值投资课程》`（7 檔，共約 10.2 小時）。
2. Whisper large-v3-turbo 在學生發言段落卡成「對對對」「玩玩玩」，最長一段 30 分鐘全毀（第 6 講）。
   - 使用者問有沒有更好的模型，裁決：「3. 先改用 SenseVoice／Paraformer 重轉 測試看效果如何」
   - 測試 15 分鐘片段：兩個模型都轉出 Whisper 壞區的內容，專有名詞較準（「宇通客車」對，Whisper 錯成「與同客車」）。Paraformer 斷句較碎；SenseVoice 沒有逐句時間戳，不能做 SRT。
   - 裁決：「1」（Whisper 為主，壞區用 Paraformer 補）
3. 第 1 輪偵測只抓「去標點後唯一字 ≤2」，漏掉「神聖上的」「對消費者」「謝謝大家」這類多字片語迴圈。第 2 輪加上「與相鄰條目相同且唯一字 ≤6」。
   - 兩輪共補回約 4 萬字。第 4 講三段收音不良（講者同時拿兩支麥克風），重轉後仍難辨識。
4. 筆記產出在 `infoAggr/北京大學價值投資課程/`（`infoAggr` 不是 git repo）：6 份分講筆記、1 份彙總、7 個 `.zh-tw.srt`。第 7 講是李錄 2019-11 北大演講，`infoAggr/李錄/` 已有兩份筆記，不重複萃取。
5. 裁決：「收進 shc-distill/scripts/」→ 修兩處後複製。
6. 裁決：「commit」→ `420c17d`，只 commit 這 3 個新檔。

</details>

<details>
<summary><b>給下一個接手者的注意事項</b></summary>

- `funasr_patch.py` 需要另外的環境：`uv run --python 3.11 --with funasr --with modelscope --with torch --with torchaudio --with opencc-python-reimplemented python -I funasr_patch.py <WORK_DIR> <PART_ID>...`。第一次執行要下載約 1GB 模型，需關沙箱。
- WORK_DIR 內要有 `{PART_ID}.mp3`（可用符號連結）與 `{PART_ID}.{SRC_SUFFIX}.srt`。`DRY=1` 只列壞區。`SRC_SUFFIX` 與 `OUT_SUFFIX` 相同時會覆寫來源。
- `whisper_stt_long.py` 在背景執行時，輸出目錄放在專案目錄內就能正常持久化。舊記憶說「背景寫 `/tmp` 會遺失」，這次沒有遇到，因為輸出不在 `/tmp`。
- `srt_to_paragraphs.py` 的輸出每行約 300 字。子代理 Read 要用 `limit=30` 分批，一次讀整檔會被截斷。
- `cleanup_epub_txt.py` 會刪掉目標目錄下所有 `_tmp_extract*`。不要對 `infoAggr` 根目錄執行，先把暫存目錄搬進該次的作者目錄再清。

</details>

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

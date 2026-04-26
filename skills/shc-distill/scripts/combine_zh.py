"""合併翻譯批次並驗證條目數、時間戳單調性（語言無關）。

用法: uv run python3 combine_zh.py <PROJ_DIR> <TEMP_DIR> <VIDEO_ID> [TARGET_LANG] [SOURCE_FILE] [--allow-bad-timestamps]
  PROJ_DIR: 專案輸出目錄（含 {VIDEO_ID}_{TARGET_LANG}_batch_*.srt）
  TEMP_DIR: 暫存目錄（寫入 {TARGET_LANG}.combined.srt）
  VIDEO_ID: 影片 ID（用於匹配正確的批次檔）
  TARGET_LANG: 翻譯目標語言前綴（預設 "zh"，中文原文影片用 "en"）
  SOURCE_FILE: 來源 SRT 的完整路徑，用於驗證條目數（可選）
               若未提供，自動搜尋 TEMP_DIR 中的 *.en*.clean.srt
  --allow-bad-timestamps: 允許時間倒退類異常繼續（僅警告不 fail-fast）；對 end<start 類型無影響（已預設自動修復）

驗證內容：
1. 逐批加總 vs 合併後條目數
2. **逐批 diff**：找出丟條目最多的批次（便於定點補翻）
3. 與原文 SRT 的條目數比對
4. **時間戳單調性**：分兩類處理
   - end < start（子代理誤寫小時位）：**預設自動修復**（無需 flag），用下一條的 start
     作為這條的 end；最後一條 fallback start+3s。只警告、不 fail-fast。
   - 時間倒退 >10 分鐘（批次時序錯亂）：**預設 fail-fast**，列出需重翻批次編號；
     加 --allow-bad-timestamps 僅警告繼續。
"""
import glob, re, sys

# 解析 --allow-bad-timestamps 旗標（位置無關）
allow_bad_ts = False
argv = []
for a in sys.argv:
    if a == "--allow-bad-timestamps":
        allow_bad_ts = True
    else:
        argv.append(a)

proj_dir = argv[1]
temp_dir = argv[2]
video_id = argv[3]
target_lang = argv[4] if len(argv) > 4 else "zh"
source_file = argv[5] if len(argv) > 5 else None

# 決定原文語言前綴（用於逐批比對）
source_lang = "en" if target_lang == "zh" else "zh"

TS_RE = re.compile(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})')

def count_entries(text):
    return len([b for b in re.split(r'\n\n+', text.strip()) if '-->' in b])

def ts_to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)

def ms_to_ts(total_ms):
    """毫秒轉 HH:MM:SS,mmm 格式"""
    hh = total_ms // 3600000
    mm = (total_ms % 3600000) // 60000
    ss = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

def check_monotonic(text, label):
    """檢查時間戳單調性，回傳 [(kind, msg)] 列表。
    kind: 'bad_end'（end<start，子代理誤寫） 或 'backward'（時間倒退 >10 min）
    """
    issues = []
    prev_end = -1
    for idx, block in enumerate(re.split(r'\n\n+', text.strip()), 1):
        m = TS_RE.search(block)
        if not m:
            continue
        start = ts_to_ms(*m.group(1, 2, 3, 4))
        end = ts_to_ms(*m.group(5, 6, 7, 8))
        # 時間戳本身壞：end < start（小時跳躍等）
        if end < start:
            issues.append(('bad_end', f"  [{label}] 區塊 {idx}: end < start ({m.group(0)})"))
        # 或相對前一條倒退超過 10 分鐘
        elif prev_end > 0 and start + 600_000 < prev_end:
            issues.append(('backward', f"  [{label}] 區塊 {idx}: 時間倒退 ({m.group(0)})"))
        prev_end = max(prev_end, end)
    return issues

def auto_fix_bad_end(text):
    """修復 end < start 的時間戳：用下一條的 start 作為這條的 end。
    最後一條 fallback 為 start + 3000ms。回傳 (修復後文字, 修復數, 修復記錄)。"""
    blocks = re.split(r'\n\n+', text.strip())
    parsed = []  # list of (block_idx, start_ms, end_ms, match_obj)
    for bi, block in enumerate(blocks):
        m = TS_RE.search(block)
        if m:
            parsed.append((bi, ts_to_ms(*m.group(1, 2, 3, 4)),
                          ts_to_ms(*m.group(5, 6, 7, 8)), m))
        else:
            parsed.append((bi, None, None, None))

    fixes, records = 0, []
    for i, (bi, start_ms, end_ms, m) in enumerate(parsed):
        if m is None or end_ms >= start_ms:
            continue
        next_start = None
        for nxt in parsed[i+1:]:
            if nxt[1] is not None:
                next_start = nxt[1]
                break
        new_end_ms = next_start if next_start is not None else start_ms + 3000
        new_end_str = ms_to_ts(new_end_ms)
        start_str = f"{m.group(1)}:{m.group(2)}:{m.group(3)},{m.group(4)}"
        old_ts = m.group(0)
        new_ts = f"{start_str} --> {new_end_str}"
        blocks[bi] = blocks[bi].replace(old_ts, new_ts, 1)
        records.append(f"    {old_ts} → {new_ts}")
        fixes += 1

    return '\n\n'.join(blocks) + '\n', fixes, records

# === 逐批合併並驗證 ===
combined = ""
batch_files = sorted(glob.glob(f"{proj_dir}/{video_id}_{target_lang}_batch_*.srt"))
total_batch_entries = 0
batch_diffs = []  # (batch_num, source_count, target_count, diff)
all_issues = []

for f in batch_files:
    content = open(f).read()
    # 清理子代理可能殘留的 code fence 標記
    content = re.sub(r' *```(?:srt)? *', '', content)
    batch_count = count_entries(content)
    combined += content
    total_batch_entries += batch_count

    # 逐批 diff：比對同名 source batch
    m = re.search(r'batch_(\d+)\.srt$', f)
    batch_num = int(m.group(1)) if m else 0
    src_batch = f"{proj_dir}/{video_id}_{source_lang}_batch_{batch_num}.srt"
    try:
        src_count = count_entries(open(src_batch).read())
    except FileNotFoundError:
        src_count = -1
    diff = (src_count - batch_count) if src_count >= 0 else None
    batch_diffs.append((batch_num, src_count, batch_count, diff))

    # 時間戳單調性檢查
    all_issues.extend(check_monotonic(content, f"batch_{batch_num}"))

    marker = ""
    if diff is not None and diff != 0:
        marker = f"  ⚠️ 源檔 {src_count} → 譯檔 {batch_count}，丟 {diff} 條"
    print(f"  {f}: {batch_count} 條{marker}")

combined_count = count_entries(combined)
out_path = f"{temp_dir}/{target_lang}.combined.srt"
with open(out_path, "w") as out:
    out.write(combined)

# === 逐批 diff 排名 ===
lost = [b for b in batch_diffs if b[3] and b[3] > 0]
if lost:
    lost.sort(key=lambda x: -x[3])
    print("\n📉 丟條目的批次（依丟失數排序）：")
    for num, src, tgt, diff in lost:
        print(f"  batch_{num}: {src} → {tgt}（丟 {diff} 條）建議重翻此批次")

# === 時間戳單調性問題（分兩類處理）===
if all_issues:
    bad_end_issues = [msg for kind, msg in all_issues if kind == 'bad_end']
    backward_issues = [msg for kind, msg in all_issues if kind == 'backward']

    # bad_end 類型：預設自動修復（無需 flag），只警告不 fail-fast
    if bad_end_issues:
        print(f"\n⚠️ 偵測到 {len(bad_end_issues)} 個 end<start 時間戳（子代理誤寫小時位）：")
        for msg in bad_end_issues[:10]:
            print(msg)
        if len(bad_end_issues) > 10:
            print(f"  ... 還有 {len(bad_end_issues) - 10} 個")
        combined, fix_count, fix_records = auto_fix_bad_end(combined)
        if fix_count > 0:
            print(f"\n🔧 自動修復 {fix_count} 個 end<start 時間戳（用下一條 start 作為 end）：")
            for rec in fix_records[:5]:
                print(rec)
            if fix_count > 5:
                print(f"    ... 還有 {fix_count - 5} 個")
            with open(out_path, "w") as out:
                out.write(combined)
            combined_count = count_entries(combined)

    # backward 類型：預設 fail-fast（批次時序錯亂通常需重翻）
    if backward_issues:
        print(f"\n⚠️ 偵測到 {len(backward_issues)} 個時間倒退（>10 分鐘跳回）：")
        for msg in backward_issues[:10]:
            print(msg)
        if len(backward_issues) > 10:
            print(f"  ... 還有 {len(backward_issues) - 10} 個")
        bad_batches = sorted({int(m.group(1)) for msg in backward_issues
                              if (m := re.search(r'batch_(\d+)', msg))})
        if bad_batches:
            print(f"\n建議重翻批次：{bad_batches}")
        if not allow_bad_ts:
            print("\n❌ fail-fast: 時間倒退會打亂字幕時序。")
            print("   重派上述批次的翻譯子代理，再重跑本指令；或加 --allow-bad-timestamps 強制繼續。")
            sys.exit(1)
        else:
            print("\n⚠️ --allow-bad-timestamps: 時間倒退異常僅警告，繼續合併。")

# === 驗證：逐批加總 vs 合併後 ===
if total_batch_entries != combined_count:
    print(f"\n⚠️ 逐批加總 {total_batch_entries} 條 ≠ 合併後 {combined_count} 條（解析損失）")

# === 驗證：與來源檔比對 ===
if source_file:
    src_count = count_entries(open(source_file).read())
else:
    en_files = sorted(glob.glob(f'{temp_dir}/*.en*.clean.srt') + glob.glob(f'{temp_dir}/*.en-orig*.clean.srt'))
    src_count = count_entries(open(en_files[0]).read()) if en_files else 0
    source_file = en_files[0] if en_files else "(未找到)"

print(f"\nCombined {len(batch_files)} batches -> {out_path}")
print(f"驗證：來源={src_count} 條, 翻譯={combined_count} 條", end=" ")
if src_count == combined_count:
    print("✅ 一致")
elif src_count > 0 and abs(src_count - combined_count) <= 5:
    print(f"⚠️ 差 {abs(src_count - combined_count)} 條（≤5，可由時間戳對齊兜底）")
else:
    diff = abs(src_count - combined_count)
    print(f"❌ 差 {diff} 條，需檢查翻譯批次")

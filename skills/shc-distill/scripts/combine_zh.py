"""合併翻譯批次並驗證條目數、時間戳單調性（語言無關）。

用法: uv run python3 combine_zh.py <PROJ_DIR> <TEMP_DIR> <VIDEO_ID> [TARGET_LANG] [SOURCE_FILE]
  PROJ_DIR: 專案輸出目錄（含 {VIDEO_ID}_{TARGET_LANG}_batch_*.srt）
  TEMP_DIR: 暫存目錄（寫入 {TARGET_LANG}.combined.srt）
  VIDEO_ID: 影片 ID（用於匹配正確的批次檔）
  TARGET_LANG: 翻譯目標語言前綴（預設 "zh"，中文原文影片用 "en"）
  SOURCE_FILE: 來源 SRT 的完整路徑，用於驗證條目數（可選）
               若未提供，自動搜尋 TEMP_DIR 中的 *.en*.clean.srt

驗證內容：
1. 逐批加總 vs 合併後條目數
2. **逐批 diff**：找出丟條目最多的批次（便於定點補翻）
3. 與原文 SRT 的條目數比對
4. **時間戳單調性**：偵測小時跳躍等壞時間戳（子代理可能誤寫）
"""
import glob, re, sys

proj_dir = sys.argv[1]
temp_dir = sys.argv[2]
video_id = sys.argv[3]
target_lang = sys.argv[4] if len(sys.argv) > 4 else "zh"
source_file = sys.argv[5] if len(sys.argv) > 5 else None

# 決定原文語言前綴（用於逐批比對）
source_lang = "en" if target_lang == "zh" else "zh"

TS_RE = re.compile(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})')

def count_entries(text):
    return len([b for b in re.split(r'\n\n+', text.strip()) if '-->' in b])

def ts_to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)

def check_monotonic(text, label):
    """檢查時間戳是否單調遞增，回傳 (問題數, 問題列表)。"""
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
            issues.append(f"  [{label}] 區塊 {idx}: end < start ({m.group(0)})")
        # 或相對前一條倒退超過 10 分鐘
        elif prev_end > 0 and start + 600_000 < prev_end:
            issues.append(f"  [{label}] 區塊 {idx}: 時間倒退 ({m.group(0)})")
        prev_end = max(prev_end, end)
    return issues

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

# === 時間戳單調性問題 ===
if all_issues:
    print(f"\n⚠️ 偵測到 {len(all_issues)} 個時間戳問題（子代理可能誤寫）：")
    for issue in all_issues[:10]:
        print(issue)
    if len(all_issues) > 10:
        print(f"  ... 還有 {len(all_issues) - 10} 個")

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

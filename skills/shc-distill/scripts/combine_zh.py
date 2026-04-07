"""合併翻譯批次並驗證條目數（語言無關）。

用法: uv run python3 combine_zh.py <PROJ_DIR> <TEMP_DIR> <VIDEO_ID> [TARGET_LANG] [SOURCE_FILE]
  PROJ_DIR: 專案輸出目錄（含 {VIDEO_ID}_{TARGET_LANG}_batch_*.srt）
  TEMP_DIR: 暫存目錄（寫入 {TARGET_LANG}.combined.srt）
  VIDEO_ID: 影片 ID（用於匹配正確的批次檔）
  TARGET_LANG: 翻譯目標語言前綴（預設 "zh"，中文原文影片用 "en"）
  SOURCE_FILE: 來源 SRT 的完整路徑，用於驗證條目數（可選）
               若未提供，自動搜尋 TEMP_DIR 中的 *.en*.clean.srt
"""
import glob, re, sys

proj_dir = sys.argv[1]
temp_dir = sys.argv[2]
video_id = sys.argv[3]
target_lang = sys.argv[4] if len(sys.argv) > 4 else "zh"
source_file = sys.argv[5] if len(sys.argv) > 5 else None

def count_entries(text):
    return len([b for b in re.split(r'\n\n+', text.strip()) if '-->' in b])

# === 逐批合併並驗證 ===
combined = ""
batch_files = sorted(glob.glob(f"{proj_dir}/{video_id}_{target_lang}_batch_*.srt"))
total_batch_entries = 0
for f in batch_files:
    content = open(f).read()
    batch_count = count_entries(content)
    combined += content
    total_batch_entries += batch_count
    print(f"  {f}: {batch_count} 條")

combined_count = count_entries(combined)
out_path = f"{temp_dir}/{target_lang}.combined.srt"
with open(out_path, "w") as out:
    out.write(combined)

# === 驗證：逐批加總 vs 合併後 ===
if total_batch_entries != combined_count:
    print(f"⚠️ 逐批加總 {total_batch_entries} 條 ≠ 合併後 {combined_count} 條（解析損失）")

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

"""合併翻譯批次並驗證條目數。

用法: uv run python3 combine_zh.py <PROJ_DIR> <TEMP_DIR> <VIDEO_ID>
  PROJ_DIR: 專案輸出目錄（含 {VIDEO_ID}_zh_batch_*.srt）
  TEMP_DIR: 暫存目錄（寫入 zh.combined.srt，含 *.en*.clean.srt）
  VIDEO_ID: 影片 ID（用於匹配正確的批次檔）
"""
import glob, re, sys

proj_dir = sys.argv[1]
temp_dir = sys.argv[2]
video_id = sys.argv[3]

combined = ""
batch_files = sorted(glob.glob(f"{proj_dir}/{video_id}_zh_batch_*.srt"))
for f in batch_files:
    combined += open(f).read()
with open(f"{temp_dir}/zh.combined.srt", "w") as out:
    out.write(combined)

# === 驗證條目數 ===
def count_entries(text):
    return len([b for b in re.split(r'\n\n+', text.strip()) if '-->' in b])

en_files = sorted(glob.glob(f'{temp_dir}/*.en*.clean.srt') + glob.glob(f'{temp_dir}/*.en-orig*.clean.srt'))
en_count = count_entries(open(en_files[0]).read()) if en_files else 0
zh_count = count_entries(combined)
print(f"Combined {len(batch_files)} batches from {proj_dir}")
print(f"驗證：EN={en_count} 條, ZH={zh_count} 條", "✅ 一致" if en_count == zh_count else f"⚠️ 差 {abs(en_count - zh_count)} 條")

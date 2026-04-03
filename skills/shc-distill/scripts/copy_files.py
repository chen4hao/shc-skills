"""複製字幕和影音檔到最終位置。

用法: uv run python3 copy_files.py <TEMP_DIR> <DEST_DIR> <MEDIA_DIR> <PREFIX>
  TEMP_DIR: 暫存目錄（含 en.srt、zh-tw.srt、bilingual.srt 及影音檔）
  DEST_DIR: 筆記 + 字幕的儲存目錄
  MEDIA_DIR: 影音檔統一存放目錄
  PREFIX: 檔案名稱前綴（主檔名）
"""
import shutil, glob, os, sys

temp_dir = sys.argv[1]
dest_dir = sys.argv[2]
media_dir = sys.argv[3]
prefix = sys.argv[4]

os.makedirs(dest_dir, exist_ok=True)
os.makedirs(media_dir, exist_ok=True)

# 複製英文字幕
shutil.copy2(f"{temp_dir}/en.srt", f"{dest_dir}/{prefix}.en.srt")
# 複製中文字幕
shutil.copy2(f"{temp_dir}/zh-tw.srt", f"{dest_dir}/{prefix}.zh-tw.srt")
# 複製雙語字幕（檔名含 &，不可在 Bash 中直接 cp）
shutil.copy2(f"{temp_dir}/bilingual.srt", f"{dest_dir}/{prefix}.en&cht.srt")

# 複製影音檔到統一影音目錄（僅在有下載影音檔時）
media_copied = False
for ext in ["mp4", "m4a", "webm"]:
    files = glob.glob(f"{temp_dir}/*.{ext}")
    if files:
        shutil.copy2(files[0], f"{media_dir}/{prefix}.{ext}")
        print(f"Copied media: {files[0]} -> {media_dir}/{prefix}.{ext}")
        media_copied = True
        break

if not media_copied:
    print("No media file to copy (subtitles were available, skipped media download)")

print(f"Subtitles copied to {dest_dir}")

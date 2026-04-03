"""清理暫存檔案。

用法: uv run python3 cleanup.py <TEMP_DIR> [PROJ_DIR]
  TEMP_DIR: 暫存目錄（將被整個刪除）
  PROJ_DIR: 專案輸出目錄（清理暫存翻譯批次檔，可選）
"""
import shutil, glob, os, sys

temp_dir = sys.argv[1]
proj_dir = sys.argv[2] if len(sys.argv) > 2 else ""

# 清理專案目錄中的暫存翻譯批次檔
if proj_dir:
    for pattern in ["zh_batch_*.srt", "en_batch_*.srt"]:
        for f in glob.glob(os.path.join(proj_dir, pattern)):
            os.remove(f)
            print(f"Removed {f}")
    tmp_srt = os.path.join(proj_dir, "en-orig.clean.srt")
    if os.path.exists(tmp_srt):
        os.remove(tmp_srt)
        print(f"Removed {tmp_srt}")

# 清理暫存目錄
shutil.rmtree(temp_dir, True)
print(f"Cleaned up {temp_dir}")

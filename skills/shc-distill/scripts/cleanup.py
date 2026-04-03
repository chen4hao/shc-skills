"""清理暫存檔案。

用法: uv run python3 cleanup.py <TEMP_DIR> [PROJ_DIR] [VIDEO_ID]
  TEMP_DIR: 暫存目錄（將被整個刪除）
  PROJ_DIR: 專案輸出目錄（清理暫存翻譯批次檔，可選）
  VIDEO_ID: 影片 ID（僅清理此 ID 的批次檔，避免誤刪其他並行會話的檔案）
"""
import shutil, glob, os, sys

temp_dir = sys.argv[1]
proj_dir = sys.argv[2] if len(sys.argv) > 2 else ""
video_id = sys.argv[3] if len(sys.argv) > 3 else ""

# 清理專案目錄中的暫存翻譯批次檔（僅限此 video_id 的檔案）
if proj_dir:
    prefix = f"{video_id}_" if video_id else ""
    for pattern in [f"{prefix}zh_batch_*.srt", f"{prefix}en_batch_*.srt"]:
        for f in glob.glob(os.path.join(proj_dir, pattern)):
            os.remove(f)
            print(f"Removed {f}")

# 清理暫存目錄
shutil.rmtree(temp_dir, True)
print(f"Cleaned up {temp_dir}")

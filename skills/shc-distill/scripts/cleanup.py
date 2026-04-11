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
removed_count = 0
if proj_dir:
    prefix = f"{video_id}_" if video_id else ""
    # 翻譯中間檔（批次、gap、prompt、agent config）
    batch_patterns = [f"{prefix}zh_batch_*.srt", f"{prefix}en_batch_*.srt",
                      f"{prefix}en_gap_*.srt", f"{prefix}zh_gap_*.srt",
                      f"{prefix}prompt_batch_*.txt", f"{prefix}agent_config.json"]
    # srt_to_text.py 產出的純文字檔 + 主代理若把原始 clean SRT 複製進專案目錄
    # 所留下的殘餘檔（檔名含 VIDEO_ID，不是以 prefix="{VIDEO_ID}_" 開頭）
    aux_patterns = [f"{video_id}*.clean.txt", f"{video_id}*.clean.srt"] if video_id else []
    for pattern in batch_patterns + aux_patterns:
        for f in glob.glob(os.path.join(proj_dir, pattern)):
            os.remove(f)
            removed_count += 1
            print(f"Removed {f}")
    if removed_count == 0:
        print(f"WARNING: No batch files found in {proj_dir} (prefix={prefix!r})")

# 清理暫存目錄
if os.path.isdir(temp_dir):
    shutil.rmtree(temp_dir, True)
    print(f"Cleaned up {temp_dir}")
else:
    print(f"WARNING: Temp dir not found: {temp_dir}")

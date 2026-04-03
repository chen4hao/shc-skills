"""下載字幕（優先）+ 條件性下載影音檔。

用法: uv run python3 download.py <TEMP_DIR> <URL>
  TEMP_DIR: 暫存目錄 (e.g., /tmp/distill-xzQJWLWiYYE)
  URL: 影片/podcast URL
"""
import subprocess, sys, os, json, glob

temp_dir = sys.argv[1]
url = sys.argv[2]

# === 清理舊暫存檔案（保留此腳本本身，避免自刪導致 FileNotFoundError） ===
os.makedirs(temp_dir, exist_ok=True)
for f in glob.glob(os.path.join(temp_dir, "*")):
    if not f.endswith("download.py"):
        if os.path.isfile(f):
            os.remove(f)

# === 階段 1：只下載字幕 + metadata（不下載影音） ===
print("=== 階段 1：嘗試下載字幕 ===")
subprocess.run([
    "yt-dlp",
    "--cookies-from-browser", "chrome",
    "--write-subs", "--write-auto-subs",
    "--sub-langs", "en-orig,en",
    "--convert-subs", "srt",
    "--write-info-json",
    "--skip-download",
    "-o", os.path.join(temp_dir, "%(id)s.%(ext)s"),
    url
], check=True)

# === 檢查是否取得字幕 ===
srt_files = glob.glob(os.path.join(temp_dir, "*.srt")) + glob.glob(os.path.join(temp_dir, "*.vtt"))
has_subs = len(srt_files) > 0

if has_subs:
    print(f"✅ 成功取得 {len(srt_files)} 個字幕檔，跳過影音下載")
else:
    # === 階段 2：無字幕，下載完整影音檔（供後續 Whisper STT） ===
    print("⚠️ 無法取得字幕，開始下載影音檔...")
    subprocess.run([
        "yt-dlp",
        "--cookies-from-browser", "chrome",
        "--write-info-json",
        "-S", "height:720",
        "-f", "bv+ba/ba/best",
        "--merge-output-format", "mp4",
        "-o", os.path.join(temp_dir, "%(id)s.%(ext)s"),
        url
    ], check=True)
    print("✅ 影音檔下載完成")

# === 從 .info.json 讀取影片資訊 ===
info_files = glob.glob(os.path.join(temp_dir, "*.info.json"))
if info_files:
    with open(info_files[0]) as f:
        info = json.load(f)
    print(f"Title: {info.get('title', 'N/A')}")
    print(f"Channel: {info.get('channel', 'N/A')}")
    print(f"Upload date: {info.get('upload_date', 'N/A')}")
    print(f"Duration: {info.get('duration_string', 'N/A')}")
    desc = info.get('description', 'N/A')
    print(f"Description: {desc[:2000]}")

# === 輸出狀態供後續步驟判斷 ===
print(f"\nSUBS_AVAILABLE={'YES' if has_subs else 'NO'}")

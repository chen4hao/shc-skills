"""下載字幕（優先）+ 條件性下載影音檔。

用法: uv run python3 download.py <TEMP_DIR> <URL>
  TEMP_DIR: 暫存目錄 (e.g., /tmp/distill-xzQJWLWiYYE)
  URL: 影片/podcast URL

行為：
  1. Preflight：yt-dlp --dump-single-json --playlist-end 1 取得 metadata + 字幕可用性
  2. 若有字幕：只下載字幕 + metadata，跳過影音
  3. 若無字幕：下載媒體檔給後續 Whisper STT 使用
     - **純中文/純語音平台（Bilibili、喜馬拉雅、荔枝、蜻蜓、小宇宙等）自動降級為 audio-only**
       （節省 ~3-5x 磁碟與頻寬，audio 足夠給 mlx_whisper）
     - 其他平台仍下載 720p 影片
"""
import subprocess, sys, os, json, glob

temp_dir = sys.argv[1]
url = sys.argv[2]

# 純中文/純語音平台：無字幕時只下載 audio-only（Whisper STT 足夠）
AUDIO_ONLY_DOMAINS = (
    "bilibili.com", "b23.tv",
    "ximalaya.com", "lizhi.fm", "qingting.fm", "xiaoyuzhoufm.com",
)
_is_audio_only_platform = any(d in url for d in AUDIO_ONLY_DOMAINS)

# === 清理舊暫存檔案（保留此腳本本身，避免自刪導致 FileNotFoundError） ===
os.makedirs(temp_dir, exist_ok=True)
for f in glob.glob(os.path.join(temp_dir, "*")):
    if not f.endswith("download.py"):
        if os.path.isfile(f):
            os.remove(f)

# === 階段 0：Preflight 檢查字幕可用性 ===
# 用 --dump-single-json 取得 metadata 判斷是否有字幕，避免 Bilibili 等平台在
# --skip-download --write-subs 組合下錯誤退出（"No video formats found"）。
print("=== 階段 0：preflight 檢查字幕可用性 ===")
_preflight = subprocess.run([
    "yt-dlp", "--cookies-from-browser", "chrome",
    "--dump-single-json", "--playlist-end", "1", url
], capture_output=True, text=True)
_preflight_info = None
has_native_subs = False
if _preflight.returncode == 0:
    try:
        _preflight_info = json.loads(_preflight.stdout)
        _subs = _preflight_info.get('subtitles') or {}
        _auto = _preflight_info.get('automatic_captions') or {}
        has_native_subs = bool(_subs) or bool(_auto)
    except Exception as e:
        print(f"  ⚠️ Preflight JSON 解析失敗: {e}")
print(f"  可用字幕: {has_native_subs}")

# === 階段 1：只下載字幕 + metadata（不下載影音） ===
if has_native_subs:
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
elif _preflight_info is not None:
    # Preflight 成功但無字幕：直接從 preflight JSON 落地 info.json，跳過有問題的 Stage 1
    print("=== 階段 1：跳過（preflight 無可用字幕） ===")
    _info_id = _preflight_info.get('id', 'unknown')
    _info_path = os.path.join(temp_dir, f"{_info_id}.info.json")
    with open(_info_path, 'w', encoding='utf-8') as f:
        json.dump(_preflight_info, f, ensure_ascii=False)
    print(f"  已從 preflight JSON 寫入 {_info_path}")
else:
    # Preflight 也失敗：fallback 到原始 Stage 1 嘗試（可能仍會失敗，但不要整個腳本爆掉）
    print("=== 階段 1：preflight 失敗，fallback 嘗試下載字幕 ===")
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
    ], check=False)

# === 檢查是否取得字幕 ===
srt_files = glob.glob(os.path.join(temp_dir, "*.srt")) + glob.glob(os.path.join(temp_dir, "*.vtt"))
has_subs = len(srt_files) > 0

if has_subs:
    print(f"✅ 成功取得 {len(srt_files)} 個字幕檔，跳過影音下載")
else:
    # === 階段 2：無字幕，下載媒體檔（供後續 Whisper STT） ===
    if _is_audio_only_platform:
        # 純中文/純語音平台：只下載 audio-only，節省 3-5x 磁碟與頻寬
        print("⚠️ 無法取得字幕，開始下載音訊（純語音平台，audio-only）...")
        subprocess.run([
            "yt-dlp",
            "--cookies-from-browser", "chrome",
            "--write-info-json",
            "-f", "bestaudio[ext=m4a]/bestaudio/best",
            "-o", os.path.join(temp_dir, "%(id)s.%(ext)s"),
            url
        ], check=True)
        print("✅ 音訊下載完成（audio-only）")
    else:
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

"""使用 mlx_whisper 進行語音轉文字，含音量偵測與 OpenCC 繁體轉換。

用法: uv run python3 whisper_stt.py <AUDIO_PATH> <OUTPUT_DIR> [--language LANG] [--model MODEL]
  AUDIO_PATH: 音訊或影片檔案路徑
  OUTPUT_DIR: 輸出目錄（產出 .srt 檔）
  --language: 語言代碼（預設自動偵測，中文用 "zh"）
  --model: mlx_whisper 模型（預設 mlx-community/whisper-large-v3-turbo）

功能：
  1. 偵測音訊音量分佈，識別靜音段
  2. 執行 mlx_whisper 轉錄，設定 hallucination-silence-threshold 避免幻覺
  3. 若語言為中文（zh），自動用 OpenCC s2twp 將簡體轉為繁體中文
"""
import argparse, subprocess, sys, os, struct, wave, contextlib, tempfile

parser = argparse.ArgumentParser(description="Whisper STT with volume detection and OpenCC")
parser.add_argument('audio_path', help='Audio or video file path')
parser.add_argument('output_dir', help='Output directory for SRT files')
parser.add_argument('--language', default=None, help='Language code (e.g., "zh", "en")')
parser.add_argument('--model', default='mlx-community/whisper-large-v3-turbo', help='Whisper model')
args = parser.parse_args()

audio_path = args.audio_path
output_dir = args.output_dir
basename = os.path.splitext(os.path.basename(audio_path))[0]

os.makedirs(output_dir, exist_ok=True)

# === Step 1: 音量偵測 ===
print("=== Step 1: 音量偵測 ===")

# 將影音轉為 WAV 以分析音量（使用 ffmpeg）
wav_path = os.path.join(output_dir, f"{basename}_analysis.wav")
try:
    subprocess.run(
        ['ffmpeg', '-y', '-i', audio_path, '-ac', '1', '-ar', '16000',
         '-sample_fmt', 's16', wav_path],
        capture_output=True, check=True, timeout=120
    )

    # 讀取 WAV 計算音量分佈
    with contextlib.closing(wave.open(wav_path, 'rb')) as wf:
        n_frames = wf.getnframes()
        sample_rate = wf.getframerate()
        duration_sec = n_frames / sample_rate
        # 每秒取樣分析
        chunk_size = sample_rate
        silent_seconds = 0
        total_seconds = 0
        silence_threshold = 500  # RMS threshold for silence

        for _ in range(int(duration_sec)):
            frames = wf.readframes(chunk_size)
            if len(frames) < 2:
                break
            samples = struct.unpack(f'<{len(frames)//2}h', frames)
            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
            total_seconds += 1
            if rms < silence_threshold:
                silent_seconds += 1

    silent_pct = (silent_seconds / total_seconds * 100) if total_seconds > 0 else 0
    print(f"  總時長: {total_seconds}s, 靜音段: {silent_seconds}s ({silent_pct:.1f}%)")

    if silent_pct > 30:
        print(f"  ⚠️ 靜音比例偏高 ({silent_pct:.1f}%)，提高 hallucination-silence-threshold 至 2.0")
        hall_threshold = 2.0
    else:
        hall_threshold = 1.0
        print(f"  ✅ 音量分佈正常，hallucination-silence-threshold = {hall_threshold}")

    # 清理分析用的 WAV
    os.remove(wav_path)

except FileNotFoundError:
    print("  ⚠️ ffmpeg 未安裝，跳過音量偵測，使用預設 threshold")
    hall_threshold = 1.0
except Exception as e:
    print(f"  ⚠️ 音量偵測失敗 ({e})，使用預設 threshold")
    hall_threshold = 1.0

# === Step 2: 執行 mlx_whisper ===
print("\n=== Step 2: 執行 mlx_whisper ===")
cmd = [
    'mlx_whisper',
    '--model', args.model,
    '--output-format', 'srt',
    '--output-dir', output_dir,
    '--hallucination-silence-threshold', str(hall_threshold),
    '--condition-on-previous-text', 'True',
    '--temperature', '0',
]
if args.language:
    cmd.extend(['--language', args.language])
cmd.append(audio_path)

print(f"  執行: {' '.join(cmd)}")
result = subprocess.run(cmd, timeout=600)
if result.returncode != 0:
    print("❌ mlx_whisper 執行失敗")
    sys.exit(1)

srt_path = os.path.join(output_dir, f"{basename}.srt")
if not os.path.exists(srt_path):
    print(f"❌ 預期的 SRT 檔案不存在: {srt_path}")
    sys.exit(1)

# 計算條目數
with open(srt_path, 'r', encoding='utf-8') as f:
    content = f.read()
entry_count = content.count('-->')
print(f"  ✅ 轉錄完成: {entry_count} 條字幕")

# === Step 3: OpenCC 繁體轉換（僅中文） ===
detected_lang = args.language or "auto"
if detected_lang == 'zh':
    print("\n=== Step 3: OpenCC 簡轉繁 ===")
    try:
        import opencc
        converter = opencc.OpenCC('s2twp')
        converted = converter.convert(content)
        # 寫入 .zh-tw.clean.srt
        clean_path = os.path.join(output_dir, f"{basename}.zh-tw.clean.srt")
        with open(clean_path, 'w', encoding='utf-8') as f:
            f.write(converted)
        print(f"  ✅ 繁體轉換完成: {clean_path}")
        # 也更新原始 SRT
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(converted)
    except ImportError:
        print("  ⚠️ OpenCC 未安裝，跳過繁體轉換")
        print("  安裝方式: uv pip install opencc-python-reimplemented")
else:
    print(f"\n語言為 {detected_lang}，跳過 OpenCC 轉換")
    # 為非中文語言建立 clean 檔
    clean_path = os.path.join(output_dir, f"{basename}.en.clean.srt")
    import shutil
    shutil.copy2(srt_path, clean_path)
    print(f"  ✅ 複製為: {clean_path}")

print(f"\n=== 完成 ===")
print(f"SUBS_AVAILABLE=YES")

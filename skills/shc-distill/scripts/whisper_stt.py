"""使用 mlx_whisper 進行語音轉文字，含音量偵測、幻覺清理與 OpenCC 繁體轉換。

用法: uv run python3 whisper_stt.py <AUDIO_PATH> <OUTPUT_DIR> [--language LANG] [--model MODEL]
  AUDIO_PATH: 音訊或影片檔案路徑
  OUTPUT_DIR: 輸出目錄（產出 .srt 檔）
  --language: 語言代碼（預設自動偵測，中文用 "zh"）
  --model: mlx_whisper 模型（預設 mlx-community/whisper-large-v3-turbo）

功能：
  1. 偵測音訊音量分佈，識別靜音段
  2. 執行 mlx_whisper 轉錄，設定 hallucination-silence-threshold 避免幻覺
  2.5. 清理 Whisper 幻覺：移除連續重複條目（靜音/掌聲段產生的假文字）
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
duration_sec = None  # 初始化，供後續動態 timeout 計算使用
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

# 動態 timeout：max(600s, 50% 音訊時長) — 避免長音訊誤觸 timeout
if duration_sec is not None:
    whisper_timeout = max(600, int(duration_sec * 0.5))
    print(f"  Whisper timeout: {whisper_timeout}s（音訊時長 {duration_sec:.0f}s，取 50%）")
else:
    whisper_timeout = 7200  # Fallback: 2 小時
    print(f"  Whisper timeout: {whisper_timeout}s（時長未知，使用 2 小時 fallback）")
print(f"  執行: {' '.join(cmd)}")
result = subprocess.run(cmd, timeout=whisper_timeout)
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

# === Step 2.5: 清理 Whisper 幻覺 ===
print("\n=== Step 2.5: 清理 Whisper 幻覺 ===")

def clean_hallucinations(srt_text, min_repeat=3):
    """移除連續重複的 SRT 條目（Whisper 在靜音/掌聲段產生的幻覺）。

    規則：若相同文字連續出現 >= min_repeat 條，只保留第一條。
    清理後重新編號所有條目。
    """
    import re as _re
    entries = []
    lines = srt_text.split('\n')
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if _re.match(r'^\d+$', stripped) and i + 1 < len(lines) and '-->' in lines[i + 1]:
            num = int(stripped)
            ts = lines[i + 1].strip()
            text_lines = []
            k = i + 2
            while k < len(lines) and lines[k].strip() and not (
                _re.match(r'^\d+$', lines[k].strip())
                and k + 1 < len(lines)
                and '-->' in lines[k + 1]
            ):
                text_lines.append(lines[k].strip())
                k += 1
            entries.append((ts, '\n'.join(text_lines)))
            i = k
        else:
            i += 1

    if not entries:
        return srt_text, 0

    # 偵測連續重複
    cleaned = []
    removed = 0
    streak_start = 0
    while streak_start < len(entries):
        text_at_start = entries[streak_start][1]
        streak_end = streak_start + 1
        while streak_end < len(entries) and entries[streak_end][1] == text_at_start:
            streak_end += 1
        streak_len = streak_end - streak_start
        if streak_len >= min_repeat:
            # 幻覺：只保留第一條
            cleaned.append(entries[streak_start])
            removed += streak_len - 1
        else:
            # 正常：全部保留
            cleaned.extend(entries[streak_start:streak_end])
        streak_start = streak_end

    # 重新編號並組裝
    parts = []
    for idx, (ts, text) in enumerate(cleaned, 1):
        parts.append(f"{idx}\n{ts}\n{text}\n")
    return '\n'.join(parts) + '\n' if parts else '', removed

content, removed_count = clean_hallucinations(content)
if removed_count > 0:
    # 回寫清理後的 SRT
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(content)
    new_count = content.count('-->')
    print(f"  🧹 移除 {removed_count} 條幻覺條目（連續重複文字）")
    print(f"  ✅ 清理後: {new_count} 條字幕（原 {entry_count} 條）")
    entry_count = new_count
else:
    print(f"  ✅ 無幻覺條目，維持 {entry_count} 條字幕")

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

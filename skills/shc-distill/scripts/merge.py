"""產出三個版本的 SRT 字幕檔（英文、中文、雙語）。

用法: uv run python3 merge.py <TEMP_DIR> [--master <en|zh>] [--en <PATH>] [--zh <PATH>]
  TEMP_DIR: 暫存目錄（產出 en.srt、zh-tw.srt、bilingual.srt）
  --master: 主軌語言（預設 "en"）。中文原文影片用 "zh"，以保留所有原文條目。
  --en: 英文 SRT 檔案路徑（可選，預設自動搜尋 TEMP_DIR 中的 *.en*.clean.srt 或 en.combined.srt）
  --zh: 中文 SRT 檔案路徑（可選，預設自動搜尋 TEMP_DIR 中的 zh.combined.srt 或 *.zh*.clean.srt）
"""
import re, glob, sys, argparse

parser = argparse.ArgumentParser()
parser.add_argument('temp_dir')
parser.add_argument('--master', default='en', choices=['en', 'zh'])
parser.add_argument('--en', dest='en_path', default=None)
parser.add_argument('--zh', dest='zh_path', default=None)
args = parser.parse_args()

temp_dir = args.temp_dir

def ts_to_ms(ts):
    h, m, rest = ts.split(':')
    s, ms = rest.split(',')
    return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)

def parse_srt(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    entries = []
    for block in re.split(r'\n\n+', content.strip()):
        lines = block.strip().split('\n')
        ts_line = None
        text_lines = []
        for line in lines:
            if '-->' in line:
                ts_line = line.strip()
            elif ts_line is not None:
                clean = line.strip()
                if clean and not clean.isdigit():
                    text_lines.append(clean)
        if ts_line and text_lines:
            text = ' '.join(text_lines)
            m = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', ts_line)
            if m:
                entries.append({'ts': ts_line, 'text': text,
                                'start': ts_to_ms(m.group(1)), 'end': ts_to_ms(m.group(2))})
    return entries

def write_srt(path, entries_list, mode='single'):
    with open(path, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(entries_list):
            if mode == 'bilingual':
                ts, en_text, zh_text = item
                f.write(f"{idx + 1}\n{ts}\n{en_text}\n{zh_text}\n\n")
            else:
                ts, text = item
                f.write(f"{idx + 1}\n{ts}\n{text}\n\n")
    print(f"  {path}: {len(entries_list)} entries")

def find_file(explicit, globs):
    if explicit:
        return explicit
    for pattern in globs:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None

en_path = find_file(args.en_path, [
    f'{temp_dir}/en.combined.srt',
    f'{temp_dir}/*.en*.clean.srt',
    f'{temp_dir}/*.en-orig*.clean.srt',
])
zh_path = find_file(args.zh_path, [
    f'{temp_dir}/zh.combined.srt',
    f'{temp_dir}/*.zh*.clean.srt',
])

if not en_path:
    print("ERROR: No English SRT found"); exit(1)
if not zh_path:
    print("ERROR: No Chinese SRT found"); exit(1)

en_entries = parse_srt(en_path)
zh_entries = parse_srt(zh_path)
print(f"English: {len(en_entries)} entries ({en_path})")
print(f"Chinese: {len(zh_entries)} entries ({zh_path})")
print(f"Master track: {args.master.upper()}")

# === 對齊策略：以指定語言為主軌 ===
paired = []
master_entries = en_entries if args.master == 'en' else zh_entries
secondary_entries = zh_entries if args.master == 'en' else en_entries
missing_label = '（翻譯缺失）' if args.master == 'en' else '(translation missing)'

if len(master_entries) == len(secondary_entries):
    print("條目數量一致，使用 1:1 對應")
    for i, m in enumerate(master_entries):
        en_text = m['text'] if args.master == 'en' else secondary_entries[i]['text']
        zh_text = secondary_entries[i]['text'] if args.master == 'en' else m['text']
        paired.append((m['ts'], en_text, zh_text))
else:
    print(f"條目數量不一致（主軌={len(master_entries)}, 副軌={len(secondary_entries)}），使用時間戳對齊")
    for m in master_entries:
        best_sec = missing_label
        best_overlap = 0
        for s in secondary_entries:
            overlap_start = max(m['start'], s['start'])
            overlap_end = min(m['end'], s['end'])
            overlap = max(0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_sec = s['text']
        en_text = m['text'] if args.master == 'en' else best_sec
        zh_text = best_sec if args.master == 'en' else m['text']
        paired.append((m['ts'], en_text, zh_text))

# === 產出三個檔案 ===
print("產出三個 SRT 字幕檔：")
write_srt(f'{temp_dir}/en.srt',      [(ts, en) for ts, en, zh in paired])
write_srt(f'{temp_dir}/zh-tw.srt',    [(ts, zh) for ts, en, zh in paired])
write_srt(f'{temp_dir}/bilingual.srt', paired, mode='bilingual')
print("完成！")

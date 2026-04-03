"""產出三個版本的 SRT 字幕檔（英文、中文、雙語）。

用法: uv run python3 merge.py <TEMP_DIR>
  TEMP_DIR: 暫存目錄（含 *.clean.srt 和 zh.combined.srt）
"""
import re, glob, sys

temp_dir = sys.argv[1]

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

en_files = sorted(glob.glob(f'{temp_dir}/*.en*.clean.srt') + glob.glob(f'{temp_dir}/*.en-orig*.clean.srt'))
zh_files = glob.glob(f'{temp_dir}/zh.combined.srt')
if not zh_files:
    zh_files = sorted(glob.glob(f'{temp_dir}/*.zh*.clean.srt'))

if not en_files:
    print("ERROR: No English SRT found"); exit(1)
if not zh_files:
    print("ERROR: No Chinese SRT found"); exit(1)

en_entries = parse_srt(en_files[0])
zh_entries = parse_srt(zh_files[0])
print(f"English: {len(en_entries)} entries, Chinese: {len(zh_entries)} entries")

# === 對齊策略：以英文為主軌 ===
paired = []

if len(en_entries) == len(zh_entries):
    print("條目數量一致，使用 1:1 對應")
    for i, en in enumerate(en_entries):
        paired.append((en['ts'], en['text'], zh_entries[i]['text']))
else:
    print(f"條目數量不一致（EN={len(en_entries)}, ZH={len(zh_entries)}），使用時間戳對齊")
    for en in en_entries:
        best_zh = '（翻譯缺失）'
        best_overlap = 0
        for zh in zh_entries:
            overlap_start = max(en['start'], zh['start'])
            overlap_end = min(en['end'], zh['end'])
            overlap = max(0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_zh = zh['text']
        paired.append((en['ts'], en['text'], best_zh))

# === 產出三個檔案 ===
print("產出三個 SRT 字幕檔：")
write_srt(f'{temp_dir}/en.srt',      [(ts, en) for ts, en, zh in paired])
write_srt(f'{temp_dir}/zh-tw.srt',    [(ts, zh) for ts, en, zh in paired])
write_srt(f'{temp_dir}/bilingual.srt', paired, mode='bilingual')
print("完成！")

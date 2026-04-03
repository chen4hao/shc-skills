"""去重清理 YouTube 自動字幕。

用法: uv run python3 dedup.py <TEMP_DIR>
  TEMP_DIR: 暫存目錄，含下載的 SRT/VTT 字幕檔
"""
import re, html, glob, sys, os

temp_dir = sys.argv[1]

def clean_srt(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 支援 VTT 和 SRT：移除 VTT header 和樣式標籤
    content = re.sub(r'^WEBVTT\n.*?\n\n', '', content, flags=re.DOTALL)
    content = re.sub(r' align:\w+ position:\d+%', '', content)
    content = re.sub(r'<[^>]+>', '', content)

    blocks = re.split(r'\n\n+', content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        ts_line = None
        text_lines = []
        for line in lines:
            if '-->' in line:
                ts_line = line.strip().replace('.', ',')
            elif ts_line is not None:
                clean = line.strip()
                if clean and not clean.startswith('Kind:') and not clean.startswith('Language:'):
                    text_lines.append(clean)
        if ts_line and text_lines:
            text = ' '.join(text_lines)
            # === 清理 HTML 實體和講者標記 ===
            text = html.unescape(text)           # &gt; → >, &amp; → &, etc.
            text = text.replace('>>', ' ')        # YouTube 講者切換標記
            text = re.sub(r'(?:^|\s)>\s', ' ', text)  # 單獨的 > 標記
            text = re.sub(r'\s+', ' ', text).strip()
            m = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', ts_line)
            if m and text:
                entries.append({'start': m.group(1), 'end': m.group(2), 'text': text})

    if not entries:
        print(f"  {input_path}: 0 entries (empty)")
        return

    # === Phase 1：漸進式去重（條目間） ===
    merged = []
    i = 0
    while i < len(entries):
        current = entries[i]
        j = i + 1
        while j < len(entries) and j < i + 4:
            if current['text'] in entries[j]['text']:
                current = entries[j]
                j += 1
            elif entries[j]['text'] in current['text']:
                j += 1
            else:
                break
        merged.append(current)
        i = j

    deduped = [merged[0]]
    for e in merged[1:]:
        if e['text'] != deduped[-1]['text']:
            deduped.append(e)

    # === Phase 2：條目內去重 ===
    def dedup_intra(text):
        words = text.split()
        if len(words) < 6:
            return text
        clean = []
        i = 0
        while i < len(words):
            found_repeat = False
            if len(clean) >= 3:
                max_k = min(len(words) - i, len(clean))
                for k in range(max_k, 2, -1):
                    if words[i:i+k] == clean[-k:]:
                        i += k
                        found_repeat = True
                        break
            if not found_repeat:
                clean.append(words[i])
                i += 1
        return ' '.join(clean)

    for e in deduped:
        e['text'] = dedup_intra(e['text'])

    # === Phase 3：條目間新文字提取 ===
    prev_words = []
    segments = []
    for e in deduped:
        curr_words = e['text'].split()
        best_overlap = 0
        for k in range(min(len(prev_words), len(curr_words)), 0, -1):
            if prev_words[-k:] == curr_words[:k]:
                best_overlap = k
                break
        new_words = curr_words[best_overlap:] if best_overlap > 0 else curr_words
        if new_words:
            segments.append({
                'start': e['start'],
                'end': e['end'],
                'text': ' '.join(new_words)
            })
        prev_words = curr_words

    if not segments:
        segments = deduped

    # === Phase 4：合併為自然語句字幕區塊 ===
    def ts_to_ms(ts):
        h, m, rest = ts.split(':')
        s, ms = rest.split(',')
        return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)

    SENTENCE_END = re.compile(r'[.!?]["\'）\)»]*$')
    CLAUSE_BREAK = re.compile(r'[,;:\-–—]$')

    final = []
    buf_text = []
    buf_start = segments[0]['start']
    buf_end = segments[0]['end']
    buf_words = 0
    for seg in segments:
        seg_words = len(seg['text'].split())
        buf_text.append(seg['text'])
        buf_end = seg['end']
        buf_words += seg_words
        combined = ' '.join(buf_text)
        duration = ts_to_ms(buf_end) - ts_to_ms(buf_start)
        last_word = combined.rstrip().split()[-1] if combined.strip() else ''

        is_sentence_end = bool(SENTENCE_END.search(last_word))
        is_clause_break = bool(CLAUSE_BREAK.search(last_word))

        should_split = (
            (duration >= 2000 and is_sentence_end) or
            duration >= 6000 or
            (duration >= 3500 and is_clause_break) or
            (duration >= 4000 and buf_words >= 12) or
            buf_words >= 25
        )
        if should_split:
            final.append({'start': buf_start, 'end': buf_end, 'text': combined})
            buf_text = []
            buf_start = seg['end']
            buf_words = 0
    if buf_text:
        final.append({'start': buf_start, 'end': buf_end, 'text': ' '.join(buf_text)})

    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, e in enumerate(final, 1):
            f.write(f"{idx}\n{e['start']} --> {e['end']}\n{e['text']}\n\n")

    print(f"  {input_path}: {len(entries)} raw → {len(deduped)} deduped → {len(final)} final")

for f in sorted(glob.glob(os.path.join(temp_dir, '*.*'))):
    if f.endswith(('.srt', '.vtt')):
        out = re.sub(r'\.(srt|vtt)$', '.clean.srt', f)
        clean_srt(f, out)

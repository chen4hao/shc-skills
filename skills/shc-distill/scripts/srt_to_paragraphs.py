"""把 SRT 碎句合併成段落，每 60 秒開一個新段落並標 [HH:MM:SS]，給子代理閱讀用。

用法: python srt_to_paragraphs.py <SRT> <OUT_TXT>
"""
import sys


def to_sec(t):
    h, m, rest = t.split(':')
    return int(h) * 3600 + int(m) * 60 + int(rest.split(',')[0])


def main():
    src, out = sys.argv[1], sys.argv[2]
    paras = []
    cur_start, cur = None, []
    for b in open(src, encoding='utf-8').read().strip().split('\n\n'):
        lines = b.split('\n')
        if len(lines) < 3 or ' --> ' not in lines[1]:
            continue
        t = lines[1].split(' --> ')[0].strip()
        sec = to_sec(t)
        text = ' '.join(lines[2:]).strip()
        if cur_start is None or sec - cur_start >= 60:
            if cur:
                paras.append((cur_start, cur))
            cur_start, cur = sec, []
        cur.append(text)
    if cur:
        paras.append((cur_start, cur))
    with open(out, 'w', encoding='utf-8') as f:
        for s, texts in paras:
            h, r = divmod(s, 3600)
            m, sec = divmod(r, 60)
            f.write(f'[{h:02d}:{m:02d}:{sec:02d}] ' + ' '.join(texts) + '\n\n')
    chars = sum(len(t) for _, ts in paras for t in ts)
    print(f'OUT={out} paragraphs={len(paras)} chars={chars}')


if __name__ == '__main__':
    main()

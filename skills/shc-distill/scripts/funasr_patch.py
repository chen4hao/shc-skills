"""用 Paraformer-zh 重轉 Whisper SRT 的幻覺區段，並補回原字幕（中文來源專用）。

用法:
  uv run --python 3.11 --with funasr --with modelscope --with torch --with torchaudio \\
    --with opencc-python-reimplemented python -I funasr_patch.py <WORK_DIR> <PART_ID> [<PART_ID> ...]
  （第一次執行要下載約 1GB 模型，需關沙箱。）

  WORK_DIR 內需有 {PART_ID}.mp3 與 {PART_ID}.{SRC_SUFFIX}.srt
  輸出 {PART_ID}.{OUT_SUFFIX}.srt，來源檔不動（兩者相同時會覆寫來源）。

環境變數:
  SRC_SUFFIX  來源 SRT 後綴（預設 zh-tw.clean）
  OUT_SUFFIX  輸出 SRT 後綴（預設 zh-tw.patched）
  DRY=1       只列出偵測到的壞區，不重轉

流程:
  1. 找幻覺區：連續 >= 8 條幻覺條目（允許夾 2 條正常條目），且區段時長 >= 60 秒。
     幻覺條目＝去標點後唯一字元 <= 2（「對」「玩玩玩」「!」），
     或與相鄰條目相同且唯一字元 <= 6（「對消費者」「謝謝大家」這類多字片語迴圈）。
     短於 60 秒的多半是現場真的在說「對、對」，保留不動。
  2. 每區前後各多切 3 秒音訊（16kHz 單聲道 wav），用 Paraformer 轉錄。
  3. 丟掉只有標點的條目；過短的碎句合併（合併後 <= 24 字、間隔 < 1 秒）。
  4. 刪除 base 中 start 落在區段內的條目，換成 patch 中 start 落在區段內的條目。
"""
import os
import re
import subprocess
import sys

from funasr import AutoModel
from opencc import OpenCC

MIN_RUN = 8
GAP_TOL = 2
MIN_REGION_SEC = 60
PAD_SEC = 3
MERGE_MAX_CHARS = 24
MERGE_MAX_GAP_MS = 1000

cc = OpenCC('s2twp')
PUNCT = r'[\s，。！？、,.!?…~～；;：:]'


def to_ms(t):
    h, m, rest = t.split(':')
    s, ms = rest.split(',')
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def to_ts(ms):
    ms = max(0, int(ms))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def parse(path):
    out = []
    for b in open(path, encoding='utf-8').read().strip().split('\n\n'):
        lines = b.split('\n')
        if len(lines) < 3 or ' --> ' not in lines[1]:
            continue
        s, e = lines[1].split(' --> ')
        out.append([to_ms(s.strip()), to_ms(e.strip()), ' '.join(lines[2:])])
    return out


def is_hallu(text):
    core = re.sub(PUNCT, '', text)
    return core == '' or len(set(core)) <= 2


def core_of(text):
    return re.sub(PUNCT, '', text)


def find_regions(ents):
    cores = [core_of(t) for _, _, t in ents]
    flags = []
    for k, (_, _, t) in enumerate(ents):
        # 多字片語迴圈：與相鄰條目相同，且不同字數 <= 6（例如「對消費者」「謝謝大家」）
        same_nb = ((k > 0 and cores[k] == cores[k - 1]) or
                   (k + 1 < len(ents) and cores[k] == cores[k + 1]))
        flags.append(is_hallu(t) or (same_nb and len(set(cores[k])) <= 6))
    regions = []
    i, n = 0, len(ents)
    while i < n:
        if not flags[i]:
            i += 1
            continue
        j, last, normal = i, i, 0
        while j + 1 < n:
            j += 1
            if flags[j]:
                last, normal = j, 0
            else:
                normal += 1
                if normal > GAP_TOL:
                    break
        if sum(flags[i:last + 1]) >= MIN_RUN:
            rs = ents[i][0]
            # 區段終點取下一條正常條目的起點（沒有就取最後一條的終點）
            re_ = ents[last + 1][0] if last + 1 < n else ents[last][1]
            if re_ - rs >= MIN_REGION_SEC * 1000:
                regions.append((rs, re_))
        i = last + 1
    return regions


def merge_fragments(sents):
    out = []
    for s in sents:
        if out:
            prev = out[-1]
            if (len(prev[2]) + len(s[2]) <= MERGE_MAX_CHARS
                    and s[0] - prev[1] < MERGE_MAX_GAP_MS):
                prev[1] = s[1]
                prev[2] = prev[2] + s[2]
                continue
        out.append(list(s))
    return out


def transcribe_region(model, audio, rs, re_, wav):
    start = max(0, rs - PAD_SEC * 1000)
    dur = (re_ - start) + PAD_SEC * 1000
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start / 1000:.3f}',
                    '-t', f'{dur / 1000:.3f}', '-i', audio, '-ar', '16000', '-ac', '1', wav],
                   check=True)
    res = model.generate(input=wav, batch_size_s=300, sentence_timestamp=True)
    sents = []
    for s in res[0].get('sentence_info', []):
        text = cc.convert(s['text']).strip()
        if re.sub(PUNCT, '', text) == '':
            continue
        a, b = s['start'] + start, s['end'] + start
        if rs <= a < re_:
            sents.append([a, b, text])
    return merge_fragments(sents)


def main():
    work_dir, parts = sys.argv[1], sys.argv[2:]
    src_suffix = os.environ.get('SRC_SUFFIX', 'zh-tw.clean')
    out_suffix = os.environ.get('OUT_SUFFIX', 'zh-tw.patched')
    dry = os.environ.get('DRY') == '1'
    model = AutoModel(model='paraformer-zh', vad_model='fsmn-vad', punc_model='ct-punc',
                      disable_update=True)
    for pid in parts:
        base_path = os.path.join(work_dir, f'{pid}.{src_suffix}.srt')
        audio = os.path.join(work_dir, f'{pid}.mp3')
        base = parse(base_path)
        regions = find_regions(base)
        if dry:
            for rs, re_ in regions:
                print(f'REGION {pid} {to_ts(rs)} -> {to_ts(re_)} ({(re_ - rs) // 1000}s)')
            continue
        kept = base
        patches = []
        for k, (rs, re_) in enumerate(regions):
            wav = os.path.join(work_dir, f'_patch_{pid}_{k}.wav')
            new = transcribe_region(model, audio, rs, re_, wav)
            os.remove(wav)
            removed = sum(1 for e in kept if rs <= e[0] < re_)
            kept = [e for e in kept if not (rs <= e[0] < re_)]
            patches.extend(new)
            chars = sum(len(t) for _, _, t in new)
            print(f'PATCH {pid} {to_ts(rs)} -> {to_ts(re_)} removed={removed} added={len(new)} chars={chars}')
            for a, _, t in new[:2] + new[-1:]:
                print(f'    {to_ts(a)} {t}')
        merged = sorted(kept + patches, key=lambda e: e[0])
        out_path = os.path.join(work_dir, f'{pid}.{out_suffix}.srt')
        with open(out_path, 'w', encoding='utf-8') as f:
            for i, (a, b, t) in enumerate(merged, 1):
                f.write(f'{i}\n{to_ts(a)} --> {to_ts(b)}\n{t}\n\n')
        print(f'DONE {pid} regions={len(regions)} entries {len(base)} -> {len(merged)} out={out_path}')


if __name__ == '__main__':
    main()

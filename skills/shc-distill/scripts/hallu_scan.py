"""找出 Whisper SRT 的幻覺區段，合併成連續區間後印出時間範圍。

用法: python3 -I hallu_scan.py <SRT> [<SRT> ...]

幻覺條目判定：文字去掉標點後唯一字元數 <= 2（例如「對」「對對對…」「玩玩玩」「!」），
或與相鄰條目相同且唯一字元數 <= 6（例如「對消費者」「謝謝大家」這類多字片語迴圈）。
連續 >= MIN_RUN 條幻覺條目（中間允許夾 GAP_TOL 條正常條目）視為一個幻覺區。
"""
import re
import sys

MIN_RUN = 8
GAP_TOL = 2


def parse(path):
    blocks = open(path, encoding='utf-8').read().strip().split('\n\n')
    out = []
    for b in blocks:
        lines = b.split('\n')
        if len(lines) < 3:
            continue
        s, e = lines[1].split(' --> ')
        out.append((s.strip(), e.strip(), ' '.join(lines[2:])))
    return out


def is_hallu(text):
    core = re.sub(r'[\s，。！？、,.!?…~～]', '', text)
    if core == '':
        return True
    return len(set(core)) <= 2


def main():
    for path in sys.argv[1:]:
        ents = parse(path)
        cores = [re.sub(r'[\s，。！？、,.!?…~～]', '', t) for _, _, t in ents]
        flags = []
        for k, (_, _, t) in enumerate(ents):
            # 多字片語迴圈：與相鄰條目相同，且不同字數 <= 6（例如「對消費者」「謝謝大家」）
            same_nb = ((k > 0 and cores[k] == cores[k - 1]) or
                       (k + 1 < len(ents) and cores[k] == cores[k + 1]))
            flags.append(is_hallu(t) or (same_nb and len(set(cores[k])) <= 6))
        regions = []
        i = 0
        n = len(ents)
        while i < n:
            if not flags[i]:
                i += 1
                continue
            j = i
            last = i
            normal = 0
            while j + 1 < n:
                j += 1
                if flags[j]:
                    last = j
                    normal = 0
                else:
                    normal += 1
                    if normal > GAP_TOL:
                        break
            count = sum(flags[i:last + 1])
            if count >= MIN_RUN:
                regions.append((i, last, count))
            i = last + 1
        print(f'## {path.rsplit("/", 1)[-1]} entries={n} hallu_entries={sum(flags)}')
        for a, b, c in regions:
            nxt = ents[b + 1][0] if b + 1 < n else 'END'
            prv = ents[a - 1][1] if a > 0 else 'START'
            print(f'  REGION #{a + 1}-#{b + 1} ({c} hallu) {ents[a][0]} -> {ents[b][1]} | prev_end={prv} next_start={nxt}')


if __name__ == '__main__':
    main()

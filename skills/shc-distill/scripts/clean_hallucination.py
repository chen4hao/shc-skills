"""清理 SRT 字幕檔中的 Whisper 幻覺（三種偵測模式）。

Whisper 在靜音、掌聲、背景音樂、或中段 decoder 卡住時會產生幻覺。依模式偵測並移除：

  1. 預設（連續重複）    — 同文字條目連續出現 ≥min-repeat 次（掌聲/靜音段最常見）
  2. --strict            — 連續 ≥min-streak 個短字元（≤short-char）條目區，即使非完全相同
  3. --long-line-mode    — 單一條目內「同字元佔比 >dominance」的長行（中段卡住產生 30
                            秒固定區間的「對對對…」「嗯嗯嗯…」重複）

用法:
    uv run python3 clean_hallucination.py <SRT_PATH> [options]

參數:
    SRT_PATH:              要清理的 SRT 檔案路徑
    --min-repeat N         預設模式：連續重複幾條以上才視為幻覺（預設 3）
    --strict               啟用短字元密度模式（補強預設模式）
    --strict-min-streak    --strict 的最小 streak 長度（預設 20）
    --strict-char-threshold --strict 的短字元上限（預設 3）
    --long-line-mode       啟用長行單字元重複模式
    --long-line-min-chars  --long-line-mode 的最小行字元數（預設 20）
    --long-line-dominance  --long-line-mode 的最頻字元佔比閾值（預設 0.8）
    --dry-run              只報告不修改檔案

範例:
    uv run python3 clean_hallucination.py /tmp/distill-xxx/xxx.en.clean.srt
    uv run python3 clean_hallucination.py xxx.srt --strict --long-line-mode
    uv run python3 clean_hallucination.py xxx.srt --long-line-mode --dry-run
"""
import argparse
import os
import re
import sys


def parse_srt(text):
    """Parse SRT text into list of (timestamp, text_content) tuples."""
    entries = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if re.match(r'^\d+$', stripped) and i + 1 < len(lines) and '-->' in lines[i + 1]:
            ts = lines[i + 1].strip()
            text_lines = []
            k = i + 2
            while k < len(lines) and lines[k].strip() and not (
                re.match(r'^\d+$', lines[k].strip())
                and k + 1 < len(lines)
                and '-->' in lines[k + 1]
            ):
                text_lines.append(lines[k].strip())
                k += 1
            entries.append((ts, '\n'.join(text_lines)))
            i = k
        else:
            i += 1
    return entries


def clean_hallucinations(entries, min_repeat=3):
    """Remove consecutive duplicate entries. Returns (cleaned_entries, removed_count, details)."""
    cleaned = []
    removed = 0
    details = []  # (start_idx, end_idx, text, count)
    streak_start = 0

    while streak_start < len(entries):
        text_at_start = entries[streak_start][1]
        streak_end = streak_start + 1
        while streak_end < len(entries) and entries[streak_end][1] == text_at_start:
            streak_end += 1
        streak_len = streak_end - streak_start

        if streak_len >= min_repeat:
            cleaned.append(entries[streak_start])
            removed += streak_len - 1
            details.append((streak_start + 1, streak_end, text_at_start, streak_len))
        else:
            cleaned.extend(entries[streak_start:streak_end])
        streak_start = streak_end

    return cleaned, removed, details


def strict_cleanup(entries, min_streak=20, short_char_threshold=3):
    """激進的滑動視窗清理：移除任何 ≥min_streak 個連續條目都是短字元（≤short_char_threshold）
    的區域，不論文字是否完全相同。

    這是 clean_hallucinations() 的補強層——後者只偵測『文字完全相同』的 streaks，若幻覺區
    被空字串、微變異（如「誒。」「嗯啊」）打斷，就會分裂成多個小 streaks 逃過清理。
    本函數改以『短字元密度』為判準，一次捕捉整片幻覺區，只保留第一條，其餘全部移除。

    回傳 (cleaned_entries, removed_count, detected_regions)，其中
    detected_regions 是 [(start_1based, end_exclusive_1based, streak_len), ...]
    """
    if len(entries) < min_streak:
        return entries, 0, []

    to_remove = set()
    detected = []
    i = 0
    while i < len(entries):
        # 啟動 streak：所有條目文字長度 ≤ 門檻
        if len(entries[i][1].strip()) <= short_char_threshold:
            j = i
            while j < len(entries) and len(entries[j][1].strip()) <= short_char_threshold:
                j += 1
            streak_len = j - i
            if streak_len >= min_streak:
                # 保留第一條，其餘全部標記移除
                for k in range(i + 1, j):
                    to_remove.add(k)
                detected.append((i + 1, j + 1, streak_len))
            i = j
        else:
            i += 1

    cleaned = [e for idx, e in enumerate(entries) if idx not in to_remove]
    return cleaned, len(to_remove), detected


def long_line_cleanup(entries, min_chars=20, dominance=0.8):
    """偵測「單條目內同字元佔比高」的長行幻覺（Whisper decoder 中段卡住產物）。

    典型症狀：連續多條字幕都是固定 30 秒時間戳（如 `00:17:17,340 --> 00:17:47,340`），
    文字是同一字元重複數百次（「對對對…」「嗯嗯嗯…」）。`clean_hallucinations()` 抓不到
    （條目間偶爾夾真實內容打斷連續性），`strict_cleanup()` 也抓不到（這些是「長行」而非
    「短字元 streak」）。本函數以「單條目內最頻字元佔比 >dominance」為判準。

    回傳 (cleaned_entries, removed_count, details)，其中
    details = [(orig_idx_1based, ts, text_preview), ...]
    """
    from collections import Counter

    cleaned = []
    details = []
    for idx, (ts, text) in enumerate(entries, start=1):
        # 去除所有空白字元，只看實際內容
        plain = ''.join(text.split())
        if len(plain) >= min_chars:
            counter = Counter(plain)
            _, top_count = counter.most_common(1)[0]
            if top_count / len(plain) >= dominance:
                preview = plain[:30] + ('…' if len(plain) > 30 else '')
                details.append((idx, ts, preview))
                continue
        cleaned.append((ts, text))
    return cleaned, len(details), details


def entries_to_srt(entries):
    """Convert entries list to SRT text with sequential numbering."""
    parts = []
    for idx, (ts, text) in enumerate(entries, 1):
        parts.append(f"{idx}\n{ts}\n{text}\n")
    return '\n'.join(parts) + '\n' if parts else ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('srt_path', help='SRT file to clean')
    ap.add_argument('--min-repeat', type=int, default=3, help='Min consecutive repeats to trigger removal (default: 3)')
    ap.add_argument('--dry-run', action='store_true', help='Report only, do not modify file')
    ap.add_argument('--strict', action='store_true',
                    help='額外的滑動視窗清理：移除 ≥--strict-min-streak 個連續短字元條目（不論是否完全相同）')
    ap.add_argument('--strict-min-streak', type=int, default=20,
                    help='--strict 模式的最小 streak 長度（預設 20）')
    ap.add_argument('--strict-char-threshold', type=int, default=3,
                    help='--strict 模式的「短字元」上限（預設 3，即 ≤3 字元的條目被視為短條目）')
    ap.add_argument('--long-line-mode', action='store_true',
                    help='偵測單一條目內「同字元重複佔比 >dominance」的長行幻覺（中段卡住產物，如「對對對...」）')
    ap.add_argument('--long-line-min-chars', type=int, default=20,
                    help='--long-line-mode 的最小行字元數（預設 20；少於此數的短行不判定）')
    ap.add_argument('--long-line-dominance', type=float, default=0.8,
                    help='--long-line-mode 的最頻字元佔比閾值（預設 0.8）')
    args = ap.parse_args()

    if not os.path.exists(args.srt_path):
        print(f"error: file not found: {args.srt_path}", file=sys.stderr)
        return 1

    with open(args.srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = parse_srt(content)
    if not entries:
        print(f"No SRT entries found in {args.srt_path}")
        return 0

    cleaned, removed, details = clean_hallucinations(entries, args.min_repeat)

    print(f"原始條目數: {len(entries)}")

    if removed == 0:
        print(f"未偵測到連續重複幻覺（預設模式：連續重複 >= {args.min_repeat} 條）")
        # 仍然繼續到 strict / long-line 階段（兩者可獨立觸發）
    else:
        print(f"偵測到 {len(details)} 段幻覺，共 {removed} 條將被移除：")
    for start, end, text, count in details:
        preview = text[:50].replace('\n', ' ')
        print(f"  條目 {start}-{end} ({count} 條): \"{preview}...\"" if len(text) > 50 else f"  條目 {start}-{end} ({count} 條): \"{preview}\"")

    print(f"清理後條目數: {len(cleaned)}")

    # --- Long-line 模式：單條目內同字元重複佔比 ---
    if args.long_line_mode:
        cleaned, long_removed, long_details = long_line_cleanup(
            cleaned,
            min_chars=args.long_line_min_chars,
            dominance=args.long_line_dominance,
        )
        if long_removed:
            print(f"\n[--long-line-mode] 偵測到 {long_removed} 條長行幻覺（最頻字元佔比 ≥ {args.long_line_dominance:.0%}）：")
            for orig_idx, ts, preview in long_details[:10]:
                print(f"  #{orig_idx} [{ts}] {preview}")
            if long_removed > 10:
                print(f"  ... 共 {long_removed} 條")
            print(f"[--long-line-mode] 清理後條目數: {len(cleaned)}")
        else:
            print(f"\n[--long-line-mode] 無長行幻覺（最小 {args.long_line_min_chars} 字元且最頻佔比 ≥ {args.long_line_dominance:.0%}）")

    # --- Strict 模式：滑動視窗短字元區清理 ---
    if args.strict:
        cleaned, strict_removed, regions = strict_cleanup(
            cleaned,
            min_streak=args.strict_min_streak,
            short_char_threshold=args.strict_char_threshold,
        )
        if strict_removed:
            print(f"\n[--strict] 偵測到 {len(regions)} 段短字元連續區，額外移除 {strict_removed} 條：")
            for start, end, count in regions:
                print(f"  條目 {start}-{end - 1} ({count} 條，全部 ≤{args.strict_char_threshold} 字元)")
            print(f"[--strict] 清理後條目數: {len(cleaned)}")
        else:
            print(f"\n[--strict] 無連續 ≥{args.strict_min_streak} 的短字元區")

    if args.dry_run:
        print("\n(dry-run 模式，未修改檔案)")
        return 0

    output = entries_to_srt(cleaned)
    with open(args.srt_path, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n已寫入: {args.srt_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

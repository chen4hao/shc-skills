"""清理 SRT 字幕檔中的 Whisper 幻覺（連續重複條目）。

Whisper 在靜音、掌聲、背景音樂等段落常產生大量重複文字條目（hallucination）。
本腳本偵測並移除這類連續重複條目，只保留每段重複的第一條，並重新編號。

用法:
    uv run python3 clean_hallucination.py <SRT_PATH> [--min-repeat N] [--dry-run]

參數:
    SRT_PATH:     要清理的 SRT 檔案路徑
    --min-repeat: 連續重複幾條以上才視為幻覺（預設 3）
    --dry-run:    只報告不修改檔案

範例:
    uv run python3 clean_hallucination.py /tmp/distill-xxx/xxx.en.clean.srt
    uv run python3 clean_hallucination.py /tmp/distill-xxx/xxx.srt --min-repeat 5 --dry-run
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
        print(f"未偵測到幻覺（連續重複 >= {args.min_repeat} 條）")
        return 0

    print(f"偵測到 {len(details)} 段幻覺，共 {removed} 條將被移除：")
    for start, end, text, count in details:
        preview = text[:50].replace('\n', ' ')
        print(f"  條目 {start}-{end} ({count} 條): \"{preview}...\"" if len(text) > 50 else f"  條目 {start}-{end} ({count} 條): \"{preview}\"")

    print(f"清理後條目數: {len(cleaned)}")

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

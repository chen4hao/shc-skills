#!/usr/bin/env python3
"""Detect Whisper hallucination gaps in SRT for batch ffmpeg-cut + re-STT.

Usage:
  detect_srt_gaps.py <srt_path> [--min-jump-sec N] [--min-repeat N]
                                [--min-blank N] [--description-timeline "TS|TS|..."]
                                [--total-duration-sec N] [--density-threshold N]

Scans SRT for four gap patterns and prints actionable cut commands so the
main agent doesn't have to read the entire SRT into context.

Patterns:
  1. Time jump      — entry[N+1].start - entry[N].end > min_jump_sec
  2. Repeat hallucination — entry text contains same char repeated >= min_repeat
  3. Blank entry block    — >= min_blank consecutive entries with empty text
  4. Density gap (optional) — for each description timeline window, density
                              < density_threshold entries/min flags suspect gap

For each detected gap, prints the ffmpeg cut command + whisper_stt.py command
ready to paste. Also prints a summary patch_srt.py command stub.

Inputs:
  srt_path                  the .zh-tw.clean.srt to scan
  --min-jump-sec N          time-jump threshold in seconds (default 30)
  --min-repeat N            consecutive-char repeat threshold (default 5)
  --min-blank N             consecutive blank-entry threshold (default 2)
  --description-timeline    optional "MM:SS;MM:SS;..." semicolon-separated
                            timeline boundaries from YouTube description
  --total-duration-sec N    total media duration; required when timeline used
  --density-threshold N     entries-per-minute below which a window is suspect
                            (default 5)

Why this exists:
  feedback_whisper_gap_full_scan.md — STT 完成後第一時間做完整缺口掃描，
  禁分批切段。本腳本一次性產生所有缺口的 cut 指令清單，避免主代理通讀
  SRT (~4K tokens) + 多輪 round-trip。

  feedback_description_timeline_gap_check.md — 用 description 時段覆蓋
  做密度驗證，捕捉 entry 時間戳看似連續但實際是 hallucination 的情況。
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SrtEntry:
    idx: int
    start_sec: float
    end_sec: float
    text: str


TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")


def parse_srt(path: str) -> list[SrtEntry]:
    raw = Path(path).read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", raw.strip())
    entries: list[SrtEntry] = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        m = TIME_RE.search(lines[1])
        if not m:
            continue
        h1, mi1, s1, ms1, h2, mi2, s2, ms2 = m.groups()
        start = int(h1) * 3600 + int(mi1) * 60 + int(s1) + int(ms1) / 1000
        end = int(h2) * 3600 + int(mi2) * 60 + int(s2) + int(ms2) / 1000
        text = "\n".join(lines[2:]).strip()
        entries.append(SrtEntry(idx=idx, start_sec=start, end_sec=end, text=text))
    return entries


def detect_time_jumps(entries: list[SrtEntry], min_jump: float) -> list[tuple[float, float, str]]:
    gaps = []
    for prev, curr in zip(entries, entries[1:]):
        jump = curr.start_sec - prev.end_sec
        if jump > min_jump:
            gaps.append((prev.end_sec, curr.start_sec, f"time-jump {jump:.1f}s"))
    return gaps


def detect_repeat_hallucinations(entries: list[SrtEntry], min_repeat: int) -> list[tuple[float, float, str]]:
    gaps = []
    pattern = re.compile(r"(.)\1{" + str(min_repeat - 1) + r",}")
    for e in entries:
        if not e.text:
            continue
        m = pattern.search(e.text)
        if m:
            ch = m.group(1)
            run_len = len(m.group(0))
            gaps.append((e.start_sec, e.end_sec, f"repeat '{ch}'×{run_len}"))
    return gaps


def detect_blank_blocks(entries: list[SrtEntry], min_blank: int) -> list[tuple[float, float, str]]:
    gaps = []
    run_start_idx = None
    for i, e in enumerate(entries):
        if not e.text:
            if run_start_idx is None:
                run_start_idx = i
        else:
            if run_start_idx is not None and i - run_start_idx >= min_blank:
                gaps.append((entries[run_start_idx].start_sec, entries[i - 1].end_sec,
                             f"blank-block {i - run_start_idx} entries"))
            run_start_idx = None
    if run_start_idx is not None and len(entries) - run_start_idx >= min_blank:
        gaps.append((entries[run_start_idx].start_sec, entries[-1].end_sec,
                     f"blank-block {len(entries) - run_start_idx} entries"))
    return gaps


def parse_timeline_boundaries(spec: str, total_sec: float) -> list[tuple[float, float]]:
    """Parse timeline points into time windows.

    Accepts THREE formats (auto-detected per token):
      - "MM:SS"       → minutes:seconds (e.g. "3:31" = 211s)
      - "HH:MM:SS"    → hours:minutes:seconds (e.g. "1:23:45" = 5025s)
      - "NNN"         → raw seconds (e.g. "211" = 211s)

    Mixed formats in one spec are allowed: "63;3:31;7:18" = [63, 211, 438].

    Returns adjacent windows: "2:00;3:31;7:18" + total_sec=600 →
      [(120, 211), (211, 438), (438, 600)]
    """
    if not spec:
        return []
    points = []
    for token in spec.replace(",", ";").split(";"):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            parts = token.split(":")
            if len(parts) == 2:
                mm, ss = parts
                sec = int(mm) * 60 + int(ss)
            elif len(parts) == 3:
                hh, mm, ss = parts
                sec = int(hh) * 3600 + int(mm) * 60 + int(ss)
            else:
                print(f"⚠️ Skipping malformed timeline point: {token!r}", file=sys.stderr)
                continue
        else:
            try:
                sec = int(token)
            except ValueError:
                print(f"⚠️ Skipping malformed timeline point: {token!r}", file=sys.stderr)
                continue
        points.append(float(sec))
    points.append(total_sec)
    return list(zip(points, points[1:]))


def detect_density_gaps(
    entries: list[SrtEntry],
    windows: list[tuple[float, float]],
    threshold: float,
) -> list[tuple[float, float, str]]:
    gaps = []
    for win_start, win_end in windows:
        win_min = (win_end - win_start) / 60
        if win_min <= 0:
            continue
        count = sum(1 for e in entries if win_start <= e.start_sec < win_end)
        density = count / win_min
        if density < threshold:
            gaps.append((win_start, win_end,
                         f"density {density:.1f}/min ({count} entries in {win_min:.1f}min)"))
    return gaps


def merge_overlapping(gaps: list[tuple[float, float, str]], pad_sec: float = 0) -> list[tuple[float, float, list[str]]]:
    """Merge overlapping/adjacent gaps so we don't cut the same range twice."""
    if not gaps:
        return []
    sorted_gaps = sorted(gaps, key=lambda g: g[0])
    merged: list[tuple[float, float, list[str]]] = []
    cur_start, cur_end, cur_reasons = sorted_gaps[0][0], sorted_gaps[0][1], [sorted_gaps[0][2]]
    for g in sorted_gaps[1:]:
        s, e, r = g
        if s <= cur_end + pad_sec:
            cur_end = max(cur_end, e)
            cur_reasons.append(r)
        else:
            merged.append((cur_start, cur_end, cur_reasons))
            cur_start, cur_end, cur_reasons = s, e, [r]
    merged.append((cur_start, cur_end, cur_reasons))
    return merged


def fmt_time(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("srt_path")
    ap.add_argument("--min-jump-sec", type=float, default=30.0)
    ap.add_argument("--min-repeat", type=int, default=5)
    ap.add_argument("--min-blank", type=int, default=2)
    ap.add_argument("--description-timeline", default="",
                    help='"MM:SS;MM:SS;..." description timeline boundaries')
    ap.add_argument("--total-duration-sec", type=float, default=0)
    ap.add_argument("--density-threshold", type=float, default=5.0,
                    help="entries/min below this flags a density gap")
    args = ap.parse_args()

    entries = parse_srt(args.srt_path)
    if not entries:
        sys.exit(f"error: no entries parsed from {args.srt_path}")

    print(f"# Scanned {len(entries)} entries from {args.srt_path}")
    print(f"# Total duration in SRT: {fmt_time(entries[-1].end_sec)} "
          f"({entries[-1].end_sec:.0f}s)")

    all_gaps: list[tuple[float, float, str]] = []
    all_gaps.extend(detect_time_jumps(entries, args.min_jump_sec))
    all_gaps.extend(detect_repeat_hallucinations(entries, args.min_repeat))
    all_gaps.extend(detect_blank_blocks(entries, args.min_blank))

    if args.description_timeline:
        if args.total_duration_sec <= 0:
            print("⚠️ --description-timeline given but --total-duration-sec missing; "
                  "skipping density check", file=sys.stderr)
        else:
            windows = parse_timeline_boundaries(args.description_timeline,
                                                args.total_duration_sec)
            all_gaps.extend(detect_density_gaps(entries, windows, args.density_threshold))

    if not all_gaps:
        print("\n✅ No gaps detected — SRT looks clean")
        return

    merged = merge_overlapping(all_gaps, pad_sec=5.0)
    print(f"\n=== Detected {len(all_gaps)} raw gap signals → {len(merged)} merged regions ===\n")

    media_path = Path(args.srt_path).with_suffix("").with_suffix("").with_suffix("").as_posix()
    media_hint = f"{media_path}.mp4"
    tmp_dir = str(Path(args.srt_path).parent)

    patch_specs = []
    for i, (start, end, reasons) in enumerate(merged):
        seg_name = f"seg_{chr(ord('a') + i)}"
        duration = end - start
        print(f"## Gap {i + 1}: {fmt_time(start)} → {fmt_time(end)} "
              f"({duration:.0f}s)")
        print(f"   Reasons: {', '.join(reasons)}")
        print(f"   ffmpeg -ss {start:.0f} -t {duration:.0f} -i {media_hint} \\")
        print(f"     -c copy {tmp_dir}/{seg_name}.mp4 -y")
        print(f"   uv run python3 $SCRIPTS/whisper_stt.py \\")
        print(f"     {tmp_dir}/{seg_name}.mp4 {tmp_dir} --language zh")
        print()
        patch_specs.append(f"--patch {tmp_dir}/{seg_name}.zh-tw.clean.srt:{start:.0f}")

    print("=== After all whisper_stt.py finish, merge with patch_srt.py: ===\n")
    print(f"uv run python3 $SCRIPTS/patch_srt.py \\")
    print(f"  {args.srt_path} \\")
    print(f"  {args.srt_path.replace('.srt', '.patched.srt')} \\")
    for spec in patch_specs:
        print(f"  {spec}")


if __name__ == "__main__":
    main()

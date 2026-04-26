#!/usr/bin/env python3
"""Generate parallel-Read offset/limit plan for sampling a long Chinese SRT.

Usage:
  plan_srt_reads.py <srt_path> [--description-timeline "1:03;2:27;..."]
                                [--total-duration-sec N]
                                [--head-lines N] [--tail-lines N]
                                [--mid-lines N] [--num-reads N]

Reads SRT line count, computes how many entries fit, and prints a paste-ready
list of `Read offset=X limit=Y` invocations sized per
`feedback_chinese_podcast_srt_reading.md` decision table.

The point of this script is to KILL the recidivist "先 4 段試水再 2 段補讀"
anti-pattern. By computing the full sampling plan UPFRONT (during Whisper STT
wait), the agent then sends ALL N reads in one message instead of two rounds.

Decision table (from feedback_chinese_podcast_srt_reading.md):
  - <400 entries  → head 500 + tail 200 (2 reads, ~700 lines)
  - 400-800       → head 400 + 2 mid 400 + tail 200 (4 reads, ~1500 lines)
  - 800-1500      → head 300 + 3 mid 400 + tail 236 (5 reads, ~2000 lines)
  - >1500         → head 300 + 5 mid 400 + tail 236 (7 reads, ~2500 lines)

Description-timeline mode (overrides decision table when given):
  Splits SRT into N+1 segments by timeline boundaries, picks --num-reads
  segments to sample (defaults to 5-6 evenly spaced).

Why this exists:
  feedback_chinese_podcast_srt_reading.md decision table is decorative if the
  agent doesn't translate it into actual offset/limit numbers BEFORE sending
  any Read. This script does the translation, so the agent just pastes.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path


def count_lines(path: str) -> int:
    """Count lines in file. Faster than reading whole file for large SRTs."""
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def estimate_entries(line_count: int) -> int:
    """SRT entries ≈ lines / 4 (each entry: idx + time + text + blank)."""
    return line_count // 4


def parse_timeline(spec: str) -> list[float]:
    """Parse timeline tokens (MM:SS / HH:MM:SS / NNN seconds). Returns sorted seconds list."""
    if not spec:
        return []
    secs = []
    for token in spec.replace(",", ";").split(";"):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            parts = token.split(":")
            if len(parts) == 2:
                secs.append(int(parts[0]) * 60 + int(parts[1]))
            elif len(parts) == 3:
                secs.append(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
            else:
                print(f"⚠️ Skipping malformed timeline point: {token!r}", file=sys.stderr)
        else:
            try:
                secs.append(int(token))
            except ValueError:
                print(f"⚠️ Skipping malformed timeline point: {token!r}", file=sys.stderr)
    return sorted(secs)


def secs_to_lines(secs: float, total_secs: float, total_lines: int) -> int:
    """Map a time point to approximate SRT line offset (assuming uniform density)."""
    if total_secs <= 0:
        return 0
    frac = secs / total_secs
    return int(frac * total_lines)


def plan_by_decision_table(line_count: int) -> list[tuple[int, int, str]]:
    """Apply feedback_chinese_podcast_srt_reading.md decision table.

    Returns list of (offset, limit, label) tuples.
    """
    entries = estimate_entries(line_count)
    if entries < 400:
        # head + tail
        head_limit = min(500, line_count)
        tail_offset = max(0, line_count - 200)
        tail_limit = line_count - tail_offset
        return [
            (0, head_limit, f"head (entries 1~{head_limit // 4})"),
            (tail_offset, tail_limit, f"tail (last {tail_limit // 4} entries)"),
        ]
    elif entries < 800:
        # head 400 + 2 mid 400 + tail 200
        third = line_count // 4
        return [
            (0, 400, "head (0:00~7%)"),
            (third, 400, f"mid1 (~25%)"),
            (third * 2, 400, f"mid2 (~50%)"),
            (max(0, line_count - 200), min(200, line_count), "tail (last ~5%)"),
        ]
    elif entries < 1500:
        # head 300 + 3 mid 400 + tail ~236
        step = (line_count - 300 - 236) // 4
        return [
            (0, 300, "head (open ~5min)"),
            (300 + step, 400, f"mid1 (~25%)"),
            (300 + step * 2, 400, f"mid2 (~50%)"),
            (300 + step * 3, 400, f"mid3 (~75%)"),
            (max(0, line_count - 236), min(236, line_count), "tail (last ~5%)"),
        ]
    else:
        # head 300 + 5 mid 400 + tail ~236
        step = (line_count - 300 - 236) // 6
        plan = [(0, 300, "head")]
        for i in range(1, 6):
            plan.append((300 + step * i, 400, f"mid{i} (~{int(i * 100 / 6)}%)"))
        plan.append((max(0, line_count - 236), min(236, line_count), "tail"))
        return plan


def plan_by_timeline(
    line_count: int, timeline_secs: list[float], total_secs: float, num_reads: int
) -> list[tuple[int, int, str]]:
    """Plan num_reads parallel reads with line-count even spacing.

    Critical: offsets are EVENLY SPACED BY LINE COUNT, not by timeline-point count.
    Timeline points are only used to label which description segment(s) each
    read covers. This avoids the bug where timeline points densely clustered
    in early minutes cause all reads to bunch in the early section.

    Example (蕭御醫 EP244 教訓): 7 timeline points {1:03, 2:27, 5:09, 7:31,
    9:56, 11:34, 19:47} densely cluster in 0-12 min; old algorithm produced
    plan with 4/5 reads in 0-9:56 region, missing 9:56-19:47 mid (the
    "修插座" + Q&A start that advisor specifically flagged).
    """
    if not timeline_secs or total_secs <= 0:
        return plan_by_decision_table(line_count)

    # Allocate ~400 lines per read for typical 800-1500 entry case; 300 for very long
    lines_per_read = 400 if line_count < 6000 else 350

    # Even line-count spacing: head at 0, tail at end, mids evenly distributed
    if num_reads < 2:
        num_reads = 2
    last_offset = max(0, line_count - lines_per_read)
    if num_reads == 2:
        offsets = [0, last_offset]
    else:
        step = last_offset / (num_reads - 1)
        offsets = [int(round(i * step)) for i in range(num_reads)]

    # Build labels: which timeline segment(s) does each read cover?
    boundaries = [0.0] + timeline_secs + [total_secs]
    plan = []
    for i, offset in enumerate(offsets):
        limit = min(lines_per_read, max(50, line_count - offset))
        # Map offset → time → which timeline segment
        start_sec = (offset / line_count) * total_secs if line_count else 0
        end_sec = ((offset + limit) / line_count) * total_secs if line_count else 0
        # Find which timeline labels this range overlaps
        covered_pts = [s for s in timeline_secs if start_sec <= s < end_sec]
        time_label = f"{int(start_sec // 60)}:{int(start_sec % 60):02d}~{int(end_sec // 60)}:{int(end_sec % 60):02d}"
        if covered_pts:
            pts_str = ", ".join(f"{int(s // 60)}:{int(s % 60):02d}" for s in covered_pts)
            label = f"{time_label} (covers TL: {pts_str})"
        else:
            label = f"{time_label}"
        plan.append((offset, limit, label))
    return plan


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("srt_path")
    ap.add_argument("--description-timeline", default="",
                    help='"MM:SS;MM:SS;..." or "NNN;NNN;..." description timeline')
    ap.add_argument("--total-duration-sec", type=float, default=0,
                    help="total media duration in seconds (auto-derived from SRT if 0)")
    ap.add_argument("--num-reads", type=int, default=5,
                    help="how many parallel Read calls to plan (default 5)")
    args = ap.parse_args()

    srt_path = args.srt_path
    if not Path(srt_path).exists():
        sys.exit(f"error: SRT not found: {srt_path}")

    line_count = count_lines(srt_path)
    entries = estimate_entries(line_count)

    print(f"# SRT: {srt_path}")
    print(f"# Lines: {line_count}, estimated entries: {entries}")

    # Auto-derive total_duration if not given (from last SRT timestamp)
    total_secs = args.total_duration_sec
    if total_secs <= 0:
        try:
            raw = Path(srt_path).read_text(encoding="utf-8")
            ts_re = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.]\d+\s*-->")
            matches = ts_re.findall(raw)
            if matches:
                h, m, s = matches[-1]
                total_secs = int(h) * 3600 + int(m) * 60 + int(s)
        except Exception:
            pass
    print(f"# Total duration: {int(total_secs // 60)}:{int(total_secs % 60):02d} ({total_secs:.0f}s)")

    timeline_secs = parse_timeline(args.description_timeline)
    if timeline_secs:
        print(f"# Timeline boundaries: {len(timeline_secs)} points "
              f"({', '.join(str(int(s)) + 's' for s in timeline_secs)})")
        plan = plan_by_timeline(line_count, timeline_secs, total_secs, args.num_reads)
        mode = "timeline"
    else:
        print(f"# No timeline given — using decision table (entries={entries})")
        plan = plan_by_decision_table(line_count)
        mode = "decision-table"

    print(f"\n=== Sampling plan ({mode}, {len(plan)} reads, ~{sum(l for _, l, _ in plan)} lines total) ===\n")
    for offset, limit, label in plan:
        print(f"Read offset={offset} limit={limit}   # {label}")

    print(f"\n# 同訊息並行送出全部 {len(plan)} 個 Read。禁止「先 N 段試水再補讀」(見 feedback_chinese_podcast_srt_reading.md)")


if __name__ == "__main__":
    main()

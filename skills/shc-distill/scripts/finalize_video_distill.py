#!/usr/bin/env python3
"""Finalize video distill pipeline: extract -> combine -> merge -> copy -> [check] -> cleanup.

Usage:
  finalize_video_distill.py <tasks_dir> <tmp_dir> <project_dir> <video_id> <prefix> \
      [--download-dir DIR] [--target-lang zh|en] [--master en|zh] \
      [--skip-cleanup] [--check-title-terms]

One uv-run call replaces the 5 sequential script calls that previously closed out
a YouTube/podcast distill (extract_translated_batches -> combine_zh -> merge ->
copy_files -> cleanup).

--check-title-terms: opt-in sanity check that compares proper nouns from the
  YouTube title against the final EN/ZH SRTs. If a noun appears many times in
  the original .en.srt but is missing or much rarer in the .zh-tw.srt, it
  warns about possible wrong subagent term substitution. (Born from the
  2026-04-21 OpenClaw episode where subagents wrongly substituted OpenClaw
  with Claude Code throughout the translation.)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Common English stopwords / generic title words that aren't product names.
_TITLE_STOPWORDS = {
    "How", "What", "When", "Where", "Why", "Who", "Which",
    "The", "From", "With", "Your", "Their", "This", "That",
    "These", "Those", "Into", "Like", "Have", "Will", "Just",
    "Even", "Also", "True", "Life", "Believer", "Skeptic",
    "Episode", "Podcast", "Show", "Interview", "Part", "Vol",
    "Volume", "And", "But", "For", "Not", "Now", "Out", "Over",
    "Make", "Made", "Way", "Day", "Year", "Time", "World",
    "Inside", "Outside", "Future", "Past", "Best", "Most",
    "Less", "More", "About", "Against",
}


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"Step failed (exit {result.returncode}): {' '.join(cmd)}")


def check_title_terms(tmp_dir: Path, project_dir: Path, video_id: str, prefix: str,
                      extra_terms: list[str] | None = None) -> None:
    """Compare proper nouns from YouTube title + description against final SRT files.

    Catches cases where a real product/proper noun was wrongly substituted by
    subagents during translation (e.g., OpenClaw -> Claude Code, or Clawmarks
    mis-heard as Clawart in auto-captions and propagated to final SRT).

    Candidate sources (unioned):
      - Title proper nouns (capitalized, len >= 4, not stopword) — always included
      - Description proper nouns appearing >= 2 times — included (catches terms
        like OpenClaw/Felix/Clawmarks that live in description not title)
      - extra_terms (from --extra-terms CLI flag) — always included verbatim

    Verdict logic:
      - For each candidate, count occurrences in .en.srt (original) and
        .zh-tw.srt (translated)
      - If en_count >= 3 and zh_count < 30% of en_count, warn — likely wrong
        term substitution in translation.
    """
    info_path = tmp_dir / f"{video_id}.info.json"
    if not info_path.exists():
        print(f"  WARN: title-terms check skipped — {info_path.name} not found")
        return

    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARN: title-terms check skipped — could not parse info.json: {e}")
        return

    title = info.get("title", "")
    description = info.get("description", "")

    candidates: set[str] = set()

    # 1. Title proper nouns — always include
    for w in re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", title):
        if w not in _TITLE_STOPWORDS:
            candidates.add(w)

    # 2. Description proper nouns — include if appearing >= 2 times
    desc_counts: dict[str, int] = {}
    for w in re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", description):
        if w not in _TITLE_STOPWORDS:
            desc_counts[w] = desc_counts.get(w, 0) + 1
    for w, c in desc_counts.items():
        if c >= 2:
            candidates.add(w)

    # 3. Extra terms — always include verbatim
    if extra_terms:
        for w in extra_terms:
            w = w.strip()
            if w:
                candidates.add(w)

    if not candidates:
        print(f"  Title-terms check: no candidates from title/description/extra_terms")
        return

    en_srt = project_dir / f"{prefix}.en.srt"
    zh_srt = project_dir / f"{prefix}.zh-tw.srt"
    if not en_srt.exists() or not zh_srt.exists():
        print(f"  WARN: title-terms check skipped — final SRT(s) not found")
        return

    en_content = en_srt.read_text(encoding="utf-8")
    zh_content = zh_srt.read_text(encoding="utf-8")

    warnings = []
    info_lines = []
    for word in sorted(candidates):
        en_count = en_content.count(word)
        zh_count = zh_content.count(word)

        # English plural fallback: Chinese doesn't pluralize, so title terms
        # like "CPUs" / "Workloads" / "Environments" / "Agents" naturally
        # translate to the singular form in zh-tw. If the plural is absent
        # in zh-tw but the singular has matches, use singular count as the
        # effective value to avoid a false-positive title-terms warning.
        plural_note = ""
        if word.endswith("s") and len(word) > 3 and zh_count == 0:
            singular = word[:-1]
            sing_zh = zh_content.count(singular)
            if sing_zh > 0:
                zh_count = sing_zh
                plural_note = f" [via singular '{singular}']"

        info_lines.append(f"     {word}: en.srt={en_count}, zh-tw.srt={zh_count}{plural_note}")
        if en_count >= 3 and zh_count < en_count * 0.3:
            warnings.append((word, en_count, zh_count))

    print(f"\n  Title: {title}")
    print(f"  Title-terms candidates ({len(candidates)}):")
    for line in info_lines:
        print(line)

    if warnings:
        print(f"\n  ⚠️  TITLE-TERMS WARN: {len(warnings)} title term(s) appear in .en.srt but missing/rare in .zh-tw.srt:")
        for word, en_c, zh_c in warnings:
            print(f"     '{word}' — en={en_c}, zh-tw={zh_c} (ratio {zh_c / en_c:.0%})")
        print(f"  This may indicate WRONG subagent term substitution.")
        print(f"  If confirmed, restore with:")
        print(f"    uv run python3 $SCRIPTS/reverse_substitution.py \\")
        print(f"      '{project_dir}' '{prefix}' '<NEW_PREFIX>' '<wrong_term_in_zh>' '<correct_term>'")
    else:
        print(f"\n  ✓ Title-terms check passed — all {len(candidates)} title nouns appear in zh-tw.srt at expected rate")


def _parse_pairs(pairs_csv: str) -> list[tuple[str, str]]:
    """Parse mishearing pairs CSV supporting both ':' and '=' separators.

    Returns list of (wrong, correct) tuples. Skips malformed entries silently.
    """
    pairs: list[tuple[str, str]] = []
    for raw in pairs_csv.split(","):
        raw = raw.strip()
        if not raw:
            continue
        sep = None
        if ":" in raw:
            sep = ":"
        elif "=" in raw:
            sep = "="
        if sep is None:
            continue
        wrong, correct = (s.strip() for s in raw.split(sep, 1))
        if wrong and correct:
            pairs.append((wrong, correct))
    return pairs


def apply_mishearing_pairs(project_dir: Path, prefix: str, pairs_csv: str) -> None:
    """Apply mishearing pair substitutions to all three final SRTs.

    Rewrites .en.srt, .zh-tw.srt, and .en&cht.srt in-place, replacing every
    occurrence of 'wrong' with 'correct'. Prints per-file replacement counts.

    Rationale (2026-04-24 Dylan Patel × Invest Like The Best distill):
    Previously the --mishearing-pairs flag was report-only — it assumed
    subagents had already restored variants via --glossary injection during
    translation. In practice:
      (a) subagents often leave .en.srt untouched (they only rewrite zh-tw),
      (b) skill callers use '=' separator but script only recognized ':',
          silently skipping all pairs with no error.
    Fix: apply substitutions to all 3 SRTs before the report step, and accept
    both '=' and ':' as separators.
    """
    pairs = _parse_pairs(pairs_csv)
    if not pairs:
        print(f"  WARN: no valid mishearing pairs parsed (format: 'wrong=correct,wrong:correct')")
        return

    targets = [
        project_dir / f"{prefix}.en.srt",
        project_dir / f"{prefix}.zh-tw.srt",
        project_dir / f"{prefix}.en&cht.srt",
    ]

    for path in targets:
        if not path.exists():
            print(f"  SKIP (not found): {path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        before_len = len(text)
        total = 0
        for wrong, correct in pairs:
            count = text.count(wrong)
            if count:
                text = text.replace(wrong, correct)
                total += count
                print(f"  {path.name}: {wrong!r} -> {correct!r} x {count}")
        if total:
            path.write_text(text, encoding="utf-8")
            print(f"  {path.name}: {total} replacements ({before_len} -> {len(text)} bytes)")
        else:
            print(f"  {path.name}: no matches")


def check_mishearing_pairs(project_dir: Path, prefix: str, pairs_csv: str) -> None:
    """Quantify how well subagents restored known mishearing variants.

    For each pair 'wrong:correct' (or 'wrong=correct'), count:
      - 'wrong' in .en.srt (how often YouTube auto-caption misheard it)
      - 'wrong' in .zh-tw.srt (how many leaked through translation untouched)
      - 'correct' in .zh-tw.srt (how many were successfully restored)

    Print a per-pair restoration rate and warn if any 'wrong' leaked.
    Complements --check-title-terms: title-terms catches WRONG substitution
    (correct name replaced), mishearing-pairs catches MISSED restoration
    (wrong variant not restored to correct name).

    Note: If apply_mishearing_pairs() was called first, this check will show
    zero leakage by construction — that's the expected post-fix state.
    """
    en_srt = project_dir / f"{prefix}.en.srt"
    zh_srt = project_dir / f"{prefix}.zh-tw.srt"
    if not en_srt.exists() or not zh_srt.exists():
        print(f"  WARN: mishearing check skipped — final SRT(s) not found")
        return

    en_content = en_srt.read_text(encoding="utf-8")
    zh_content = zh_srt.read_text(encoding="utf-8")

    leaked = []
    for wrong, correct in _parse_pairs(pairs_csv):
        en_wrong = en_content.count(wrong)
        zh_wrong = zh_content.count(wrong)
        zh_correct = zh_content.count(correct)
        if en_wrong > 0:
            rate = 1 - (zh_wrong / en_wrong)
            print(f"     '{wrong}' → '{correct}': en.srt wrong={en_wrong}, "
                  f"zh-tw.srt wrong={zh_wrong}, zh-tw.srt correct={zh_correct} "
                  f"(restoration {rate:.0%})")
            if zh_wrong > 0:
                leaked.append((wrong, correct, zh_wrong))
        else:
            print(f"     '{wrong}' → '{correct}': en.srt wrong=0 (no mishearing to restore)")

    if leaked:
        print(f"\n  ⚠️  MISHEARING LEAK: {len(leaked)} variant(s) leaked through to zh-tw.srt:")
        for wrong, correct, n in leaked:
            print(f"     '{wrong}' still appears {n} time(s) — should be '{correct}'")
    else:
        print(f"\n  ✓ All supplied mishearing variants either restored or absent in zh-tw.srt")


def _parse_srt_entries(srt_text: str) -> list[str]:
    """Extract text content of each SRT entry (skipping index + timestamp lines)."""
    entries: list[str] = []
    for block in srt_text.split("\n\n"):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if len(lines) >= 3:
            text = " ".join(lines[2:]).strip()
            entries.append(text)
    return entries


def check_outro_drift(project_dir: Path, prefix: str, tail_entries: int = 5) -> None:
    """Heuristic detection of translation drift / hallucination in the outro.

    Subagent translation batches sometimes produce a final entry with no content
    overlap to the EN source (2026-04-24 Pachocki batch 4, 2026-04-25 Diana Hu
    batch 2 — ZH entry read '在這場競賽中，起跑點的選擇至關重要' for EN
    'operate thousand times faster than the incumbents.'). This scans the last
    N entries of .en.srt and .zh-tw.srt and warns when the ZH/EN char-ratio is
    abnormal — a cheap proxy for missing content or hallucinated filler.

    Heuristic: Chinese density is typically 0.3-0.6 of English char count. Flag
    ratio > 1.2 (ZH too long vs EN, likely outro filler) or < 0.1 (ZH too short
    or empty relative to EN).
    """
    en_srt = project_dir / f"{prefix}.en.srt"
    zh_srt = project_dir / f"{prefix}.zh-tw.srt"
    if not en_srt.exists() or not zh_srt.exists():
        print(f"  SKIP — final SRT(s) not found")
        return

    en_entries = _parse_srt_entries(en_srt.read_text(encoding="utf-8"))
    zh_entries = _parse_srt_entries(zh_srt.read_text(encoding="utf-8"))

    if len(en_entries) != len(zh_entries):
        print(f"  SKIP — entry count mismatch (en={len(en_entries)}, zh={len(zh_entries)})")
        return

    n = min(tail_entries, len(en_entries))
    flagged: list[tuple[int, str, str, float]] = []
    for idx in range(len(en_entries) - n, len(en_entries)):
        en_text = en_entries[idx]
        zh_text = zh_entries[idx]
        en_chars = len(en_text)
        zh_chars = len(zh_text)
        if en_chars == 0:
            continue
        ratio = zh_chars / en_chars
        if ratio > 1.2 or ratio < 0.1:
            flagged.append((idx + 1, en_text, zh_text, ratio))

    if flagged:
        print(f"  ⚠️  OUTRO DRIFT SUSPECTED: {len(flagged)} of last {n} entries "
              f"have abnormal ZH/EN char ratio:")
        for entry_no, en_text, zh_text, ratio in flagged:
            print(f"     Entry {entry_no} (ratio {ratio:.2f}):")
            print(f"       EN: {en_text[:80]}{'…' if len(en_text) > 80 else ''}")
            print(f"       ZH: {zh_text[:40]}{'…' if len(zh_text) > 40 else ''}")
        print(f"  Manually verify last {n} entries of .zh-tw.srt / .en&cht.srt.")
        print(f"  If drift range ≥3 entries, read .en&cht.srt once for bilingual")
        print(f"  side-by-side view, then reconcile-advisor before editing "
              f"(see feedback_srt_drift_reconcile_advisor.md).")
    else:
        print(f"  ✓ Outro drift check passed — last {n} entries have reasonable "
              f"ZH/EN char ratios")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks_dir")
    ap.add_argument("tmp_dir")
    ap.add_argument("project_dir")
    ap.add_argument("video_id")
    ap.add_argument("prefix")
    ap.add_argument("--download-dir",
                    default="/Users/chen4hao/Workspace/aiProjects/infoAggr/download")
    ap.add_argument("--target-lang", default="zh", choices=["zh", "en"])
    ap.add_argument("--master", default="en", choices=["en", "zh"])
    ap.add_argument("--source-srt", default=None,
                    help="For ZH->EN flow: path to original zh clean SRT")
    ap.add_argument("--skip-cleanup", action="store_true")
    ap.add_argument("--allow-bad-timestamps", action="store_true",
                    help="Pass through to combine_zh to allow time-backward issues (end<start is auto-fixed regardless)")
    ap.add_argument("--check-title-terms", action="store_true",
                    help="After copy, compare proper nouns from YouTube title + description against final SRTs to detect wrong subagent term substitutions")
    ap.add_argument("--extra-terms", default=None,
                    help="Comma-separated extra terms to force-check (e.g., 'OpenClaw,Felix,Clawmarks'). Catches terms that live in description but fall below the 2-occurrence threshold. Implies --check-title-terms.")
    ap.add_argument("--mishearing-pairs", default=None,
                    help="Comma-separated mishearing pairs. Format: 'wrong1=correct1,wrong2:correct2' (both '=' and ':' accepted). "
                         "Applies substitutions to all 3 final SRTs (.en.srt, .zh-tw.srt, .en&cht.srt) and then reports residual "
                         "leakage. Use to restore common YouTube auto-caption mishearings "
                         "(e.g., 'cloud code=Claude Code,Enthropic=Anthropic,Sam Alman=Sam Altman').")
    args = ap.parse_args()

    # Step 1: extract translated batches
    run(["uv", "run", "python3", str(SCRIPT_DIR / "extract_translated_batches.py"),
         args.tasks_dir, args.project_dir, args.video_id, args.target_lang])

    # Step 2: combine batches
    combine_cmd = ["uv", "run", "python3", str(SCRIPT_DIR / "combine_zh.py"),
                   args.project_dir, args.tmp_dir, args.video_id]
    if args.target_lang == "en":
        combine_cmd.extend([args.target_lang, args.source_srt or ""])
    if args.allow_bad_timestamps:
        combine_cmd.append("--allow-bad-timestamps")
    run(combine_cmd)

    # Step 3: merge three SRTs
    merge_cmd = ["uv", "run", "python3", str(SCRIPT_DIR / "merge.py"), args.tmp_dir]
    if args.master != "en":
        merge_cmd.extend(["--master", args.master])
    run(merge_cmd)

    # Step 4: copy to final locations
    run(["uv", "run", "python3", str(SCRIPT_DIR / "copy_files.py"),
         args.tmp_dir, args.project_dir, args.download_dir, args.prefix])

    # Step 4.4: outro drift heuristic check (always on) — catches the
    # 2026-04-24 Pachocki / 2026-04-25 Diana Hu pattern where the final
    # subagent batch hallucinates the outro (ZH has no content overlap with EN).
    print("\n=== Outro drift heuristic check ===", flush=True)
    check_outro_drift(Path(args.project_dir), args.prefix)

    # Step 4.5: optional sanity check (must run before cleanup deletes info.json)
    if args.check_title_terms or args.extra_terms:
        print("\n=== Title-terms sanity check ===", flush=True)
        extra_terms = args.extra_terms.split(",") if args.extra_terms else None
        check_title_terms(Path(args.tmp_dir), Path(args.project_dir),
                          args.video_id, args.prefix, extra_terms)

    # Step 4.6: optional mishearing pair application + quantification
    #   (apply first so .en.srt / .zh-tw.srt / .en&cht.srt all get fixed,
    #    then report — previously was report-only, which left .en.srt untouched)
    if args.mishearing_pairs:
        print("\n=== Mishearing pair application ===", flush=True)
        apply_mishearing_pairs(Path(args.project_dir), args.prefix,
                               args.mishearing_pairs)
        print("\n=== Mishearing restoration check ===", flush=True)
        check_mishearing_pairs(Path(args.project_dir), args.prefix,
                               args.mishearing_pairs)

    # Step 5: cleanup
    if not args.skip_cleanup:
        run(["uv", "run", "python3", str(SCRIPT_DIR / "cleanup.py"),
             args.tmp_dir, args.project_dir, args.video_id])

    print("\n✅ Finalize complete", flush=True)


if __name__ == "__main__":
    main()

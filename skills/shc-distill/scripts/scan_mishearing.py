#!/usr/bin/env python3
"""Scan SRT for known YouTube auto-caption mishearing patterns.

Usage:
  uv run python3 scan_mishearing.py <SRT_PATH>

Output:
  - stderr: human-readable summary of detected mishearings
  - stdout: comma-separated 'wrong=correct' pair string ready to paste into
            finalize_video_distill.py --mishearing-pairs

Source of patterns: feedback_youtube_mishearing_common.md (the canonical
mishearing dictionary the skill has accumulated). Update this list when
new pairs are added there.
"""
from __future__ import annotations

import sys
import pathlib

# Stable, long-lived mishearings (company / product / person names).
# Order matters for --mishearing-pairs application: longer / more specific
# patterns first to avoid partial-match collisions.
PATTERNS: list[tuple[str, str]] = [
    # Multi-word, most specific first
    ("Andre Karpathy", "Andrej Karpathy"),
    ("Boris Churnney", "Boris Cherny"),
    ("Sam Alman", "Sam Altman"),
    ("Mark Andre", "Marc Andreessen"),
    ("Daria Amodei", "Dario Amodei"),
    ("Hi, I'm Gary", "Hi, I'm Garry"),
    # Phrases that may collide with literal words → require user verification
    # before applying (printed to stderr only, not pasted to stdout).
    # ("cloud code", "Claude Code"),  # collides with literal "cloud" usage
    # SaaS / solo-founder interview artifacts (Tibo Louis-Lucas, etc.)
    ("Typrame", "Typeframe"),
    # Single-word, unambiguous
    ("clawed code", "Claude Code"),
    ("cla code", "Claude Code"),
    ("Enthropic", "Anthropic"),
    ("Verscell", "Vercel"),
    ("Replet", "Replit"),
    ("Palunteer", "Palantir"),
    ("Posterus", "Posterous"),
    ("Turboax", "TurboTax"),
    ("playrite", "Playwright"),
    ("Playright", "Playwright"),
    ("chat GBT", "ChatGPT"),
    ("ChachiPT", "ChatGPT"),
    ("Opus 47", "Opus 4.7"),
    ("1099 ins", "1099-INTs"),
    # Common transcription artifacts (2026-04-30 Karpathy distill additions)
    ("co-ound", "co-founded"),  # "co-ound open AAI" → "co-founded OpenAI"
    ("open AAI", "OpenAI"),  # frequent OpenAI mis-segmentation
    # GStack / Garry Tan family (this skill / podcast frequently)
    ("gritan", "garrytan"),
    ("GSAC", "GStack"),
    ("Gary mode", "Garry mode"),
    # Academic / neuroscience names (Huberman Lab, Lex Fridman, etc.)
    ("Bruce Mchuan", "Bruce McEwen"),
    ("Susumu Tonagawa", "Susumu Tonegawa"),
    ("Eric Kandell", "Eric Kandel"),
    ("Seapolski", "Sapolsky"),
    # James McGaugh / Larry Cahill memory-research cluster
    ("James McGaw", "James McGaugh"),
    ("Larry Kah Hill", "Larry Cahill"),
    ("McGawan Kill", "McGaugh and Cahill"),
    ("McGon Cahill", "McGaugh and Cahill"),
    ("McGon Kahill", "McGaugh and Cahill"),
    ("Macau and Cahill", "McGaugh and Cahill"),
    # Scientific term mishearings (frequent in neuroscience / health podcasts)
    ("opthalmology", "ophthalmology"),
    ("hippocample", "hippocampal"),
    ("pharmarmacology", "pharmacology"),
    ("osteocalin", "osteocalcin"),
    ("condition place preference", "conditioned place preference"),
    ("condition place avoidance", "conditioned place avoidance"),
    ("condition place aversion", "conditioned place aversion"),
    ("déja vu", "déjà vu"),
    ("deja vu", "déjà vu"),
]

# Phrases that need human OK before applying (could match literal usage)
RISKY: list[tuple[str, str, str]] = [
    ("cloud code", "Claude Code",
     "may collide with literal 'cloud' usage; verify context before adding"),
    ("Cloud code", "Claude Code",
     "same as 'cloud code' but capitalized; verify context"),
]


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: uv run python3 scan_mishearing.py <SRT_PATH>")
    srt = pathlib.Path(sys.argv[1])
    if not srt.exists():
        sys.exit(f"file not found: {srt}")

    text = srt.read_text(encoding="utf-8")

    found: list[tuple[str, str, int]] = []
    for wrong, correct in PATTERNS:
        c = text.count(wrong)
        if c:
            found.append((wrong, correct, c))

    risky_hits: list[tuple[str, str, int, str]] = []
    for wrong, correct, note in RISKY:
        c = text.count(wrong)
        if c:
            risky_hits.append((wrong, correct, c, note))

    if not found and not risky_hits:
        print(
            f"No known mishearings detected in {srt.name}.",
            file=sys.stderr,
        )
        return

    print(f"=== Detected mishearings in {srt.name} ===", file=sys.stderr)
    for wrong, correct, c in found:
        print(f"  {wrong!r} (x{c}) → {correct!r}", file=sys.stderr)

    if risky_hits:
        print("", file=sys.stderr)
        print("=== Risky candidates (NOT auto-emitted, verify first) ===",
              file=sys.stderr)
        for wrong, correct, c, note in risky_hits:
            print(f"  {wrong!r} (x{c}) → {correct!r}  [{note}]",
                  file=sys.stderr)

    if found:
        # Comma-separated string ready for finalize --mishearing-pairs
        pairs_str = ",".join(f"{w}={c}" for w, c, _ in found)
        print("", file=sys.stderr)
        print("Pair string (paste into --mishearing-pairs):", file=sys.stderr)
        print(pairs_str)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PDF book preparation pipeline for shc-distill.

One-shot: pdftotext + s2twp (OpenCC) + split by chapter marker.
Optionally probes PDF outline (bookmarks), extracts letter-labeled
appendices, and filters to a chapter subset.

Usage:
    uv run --with opencc-python-reimplemented python3 \\
      $SCRIPTS/pdf_book_prep.py <pdf_path> <extract_dir> [flags]

Key flags:
    --no-s2twp                   Skip 簡→繁 conversion (for English books)
    --preset {english,chinese-numbered,chinese-section,incerto}
                                 Chapter marker preset (default: english)
    --marker-regex PATTERN       Override preset with custom regex
    --select-chapters "1,3,7-9"  Only keep numbered chapters matching spec
    --select-appendices "A,F,G"  Additionally extract letter-labeled appendices
    --isolate                    Append PDF md5 suffix to extract_dir for session isolation

Outputs to stdout (for agent parsing):
    EXTRACT_DIR=<absolute path>
    CHAPTER_COUNT=<N>
    CHAPTERS=[(1, 'ch01.txt', <size_kb>), ...]
    BOOKMARKS=<true|false>  (indicates if PDF outline was available)

Produces files in <extract_dir>:
    full.txt        - whole-book pdftotext output (traditional Chinese if s2twp)
    front.txt       - pre-chapter-1 front matter
    ch01.txt..chNN.txt - per-chapter files (content only, no cross-chapter text)
    appF.txt        - letter-labeled appendix (if --select-appendices used)
    outline.txt     - PDF bookmarks if available (fallback chapter titles source)

Chapter titles: pdftotext usually CANNOT extract Chinese art-font chapter
titles (they live as images in the chapter frontispiece). Bookmarks are
the authoritative source. If no bookmarks exist, subagents must infer
titles from chapter opening content (less reliable).

CRITICAL: pdftotext output contains \\x0c (form-feed) page boundaries.
Python's str.splitlines() treats \\x0c as a line separator, causing list
indices to drift ahead of grep -n / Read tool line numbers. We use
.split("\\n") and strip \\x0c so line numbers stay aligned.
See feedback_pdf_form_feed_splitlines.md.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MARKER = r"^\s*CHAPTER\s+(\d+)\s*$"

# Preset markers for different book languages/layouts.
# Note: Chinese SCANNED PDF books often cannot be reliably split by regex on
# pdftotext output — chapter title pages are typically art-font images that OCR
# misreads heavily. For such books, use PyMuPDF-based 2-stage cover detection
# instead (see memory: feedback_scanned_pdf_workflow.md).
MARKER_PRESETS: dict[str, str] = {
    "english": r"^\s*CHAPTER\s+(\d+)\s*$",
    # Chinese text-based PDFs (NOT scanned). Tries common Chinese chapter markers.
    # The captured group is the chapter number (Arabic digits); Chinese numerals
    # are matched but not captured as int (use arabic in TOC if possible).
    "chinese-numbered": r"^\s*第\s*(\d+)\s*章\b",
    # "CHN-M" section-style marker (e.g. 陳俊旭 health book). Captures chapter N.
    # Use when each chapter starts with "CH{N}-1 一定要破解的…".
    "chinese-section": r"^\s*CH(\d+)-1\b",
    # Taleb "Technical Incerto" series and LaTeX+ArsClassica-typeset academic books.
    # Chapter headers use letter-spaced dispersed caps ("1    P R O L O G U E")
    # OR occasionally consecutive caps ("7    LIMIT DISTRIBUTIONS") due to pdftotext
    # inconsistency. This preset matches both forms. Letter-labeled appendices
    # (e.g. "F    W H AT A R E...", "A    S P E C I A L...") are NOT matched by
    # this preset — use --select-appendices to pick them.
    "incerto": r"^\s*(\d+)\s{3,}[A-Z][A-Z\s,'\-\.]{5,}",
}


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def pdf_to_text(pdf: Path, out_dir: Path) -> Path:
    """pdftotext -layout. Requires poppler (brew install poppler)."""
    if not which("pdftotext"):
        print("ERROR: pdftotext not found. Install: brew install poppler", file=sys.stderr)
        sys.exit(1)
    full_txt = out_dir / "full.txt"
    run(["pdftotext", "-layout", str(pdf), str(full_txt)])
    if not full_txt.exists() or full_txt.stat().st_size == 0:
        print(
            f"ERROR: pdftotext produced empty output: {full_txt}\n"
            f"  → PDF is likely SCANNED (no text layer). Run OCR first:\n"
            f"    brew install ocrmypdf tesseract-lang   # one-time\n"
            f"    ocrmypdf -l chi_tra+eng --output-type pdf {pdf} {pdf.with_suffix('.ocr.pdf')}\n"
            f"  Then re-run this script on the OCR'd PDF.\n"
            f"  For scanned Chinese books, prefer PyMuPDF 2-stage detection "
            f"(see memory: feedback_scanned_pdf_workflow.md).",
            file=sys.stderr,
        )
        sys.exit(1)
    size = full_txt.stat().st_size
    if size < 1024:
        print(
            f"WARNING: pdftotext output very small ({size} bytes). "
            f"PDF may be scanned with partial text, or mostly images. "
            f"Consider OCR + PyMuPDF flow (feedback_scanned_pdf_workflow.md).",
            file=sys.stderr,
        )
    return full_txt


def opencc_convert(text_path: Path) -> None:
    """In-place convert 簡體 → 繁體台灣正體含用語 (s2twp)."""
    try:
        from opencc import OpenCC  # type: ignore
    except ImportError:
        print(
            "ERROR: opencc-python-reimplemented not available. Run with:\n"
            "  uv run --with opencc-python-reimplemented python3 ...",
            file=sys.stderr,
        )
        sys.exit(1)
    cc = OpenCC("s2twp")
    src = text_path.read_text(encoding="utf-8")
    text_path.write_text(cc.convert(src), encoding="utf-8")


def try_pdf_outline(pdf: Path, out_dir: Path) -> bool:
    """Try to extract PDF bookmarks. Returns True if outline was written."""
    outline_path = out_dir / "outline.txt"

    # Try mutool first (more reliable for Chinese)
    if which("mutool"):
        try:
            r = run(["mutool", "show", str(pdf), "outline"], check=False)
            if r.returncode == 0 and r.stdout.strip():
                outline_path.write_text(r.stdout, encoding="utf-8")
                return True
        except Exception:
            pass

    # Fallback: pdfinfo
    if which("pdfinfo"):
        try:
            r = run(["pdfinfo", "-listbookmark", str(pdf)], check=False)
            if r.returncode == 0 and r.stdout.strip():
                outline_path.write_text(r.stdout, encoding="utf-8")
                return True
        except Exception:
            pass

    return False


def load_lines(full_txt: Path) -> list[str]:
    """Read full.txt and split into lines with form-feed stripped.

    CRITICAL: use split("\\n") not splitlines(keepends=True). pdftotext emits
    \\x0c (form-feed, PDF page boundary) chars; str.splitlines() treats \\x0c as
    a line separator, causing Python list indices to drift ahead of grep -n /
    Read tool line numbers. We strip \\x0c so subagents see clean text.
    See feedback_pdf_form_feed_splitlines.md.
    """
    text = full_txt.read_text(encoding="utf-8").replace("\x0c", "")
    # Keep trailing newline so "".join(lines) reconstructs the text.
    return [ln + "\n" for ln in text.split("\n")]


def split_chapters(
    full_txt: Path, out_dir: Path, marker_re: str
) -> list[tuple[int, str, int]]:
    """Split full.txt into ch{NN}.txt by chapter marker.

    Returns [(num, filename, size_bytes)].
    """
    pattern = re.compile(marker_re)
    lines = load_lines(full_txt)

    markers: list[tuple[int, int]] = []  # (line_idx, chapter_num)
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            try:
                num = int(m.group(1))
                markers.append((i, num))
            except (IndexError, ValueError):
                continue

    if not markers:
        print(
            f"ERROR: no chapter markers found (regex: {marker_re})\n"
            f"  → Try a different preset: --preset chinese-numbered | chinese-section | incerto\n"
            f"  → Or supply --marker-regex 'YOUR_PATTERN' explicitly\n"
            f"  → If PDF is SCANNED Chinese book, OCR'd chapter title pages often\n"
            f"    fail regex matching (art-font headings). Use PyMuPDF 2-stage\n"
            f"    cover detection instead (see feedback_scanned_pdf_workflow.md).",
            file=sys.stderr,
        )
        sys.exit(1)

    # front matter
    front_end = markers[0][0]
    front = "".join(lines[:front_end])
    (out_dir / "front.txt").write_text(front, encoding="utf-8")

    # per-chapter
    results: list[tuple[int, str, int]] = []
    for idx, (start, num) in enumerate(markers):
        end = markers[idx + 1][0] if idx + 1 < len(markers) else len(lines)
        content = "".join(lines[start:end])
        fname = f"ch{num:02d}.txt"
        (out_dir / fname).write_text(content, encoding="utf-8")
        results.append((num, fname, len(content.encode("utf-8"))))

    return results


def split_appendices(
    full_txt: Path, out_dir: Path, letters: list[str]
) -> list[tuple[str, str, int]]:
    """Extract letter-labeled appendices (e.g. 'F    W H AT A R E...').

    Matches headers that start with a single uppercase letter + 3+ spaces +
    uppercase chars (same dispersed-caps / consecutive-caps convention as
    the 'incerto' preset). Letter filter is case-insensitive. End boundary
    = next letter-appendix OR next numbered-chapter header, whichever
    comes first.
    """
    lines = load_lines(full_txt)
    letters_upper = {L.strip().upper() for L in letters if L.strip()}
    if not letters_upper:
        return []

    # Letter-appendix header: single uppercase letter + 3+ spaces + uppercase
    app_pat = re.compile(r"^([A-Z])\s{3,}[A-Z][A-Z\s,'\-\.]{5,}")
    # Numbered-chapter header (same form as 'incerto' preset)
    num_pat = re.compile(r"^\s*(\d+)\s{3,}[A-Z][A-Z\s,'\-\.]{5,}")

    app_markers: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = app_pat.match(line)
        if m and m.group(1) in letters_upper:
            app_markers.append((i, m.group(1)))

    results: list[tuple[str, str, int]] = []
    for idx, (start, letter) in enumerate(app_markers):
        # End at next letter-appendix OR next numbered-chapter
        end = len(lines)
        if idx + 1 < len(app_markers):
            end = app_markers[idx + 1][0]
        for j in range(start + 1, end):
            if num_pat.match(lines[j]):
                end = j
                break
        content = "".join(lines[start:end])
        fname = f"app{letter}.txt"
        (out_dir / fname).write_text(content, encoding="utf-8")
        results.append((letter, fname, len(content.encode("utf-8"))))

    return results


def parse_chapter_selection(spec: str) -> set[int]:
    """Parse '1,3,7-9,22-24' into {1,3,7,8,9,22,23,24}."""
    wanted: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            wanted.update(range(int(lo), int(hi) + 1))
        elif part:
            wanted.add(int(part))
    return wanted


def compute_extract_dir(pdf: Path, base: Path, isolate: bool) -> Path:
    """Optionally append PDF md5 hash suffix for session isolation."""
    if not isolate:
        return base
    h = hashlib.md5(pdf.read_bytes()[:4096]).hexdigest()[:8]
    return Path(str(base) + f"_{h}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path, help="Path to PDF file")
    ap.add_argument("extract_dir", type=Path, help="Output directory (will be created)")
    ap.add_argument("--no-s2twp", action="store_true", help="Skip 簡→繁 conversion")
    ap.add_argument(
        "--marker-regex",
        default=None,
        help=r"Chapter marker regex (overrides --preset; default preset: english)",
    )
    ap.add_argument(
        "--preset",
        choices=list(MARKER_PRESETS.keys()),
        default="english",
        help=(
            "Chapter marker preset. 'english' (default, 'CHAPTER N'), "
            "'chinese-numbered' (第 N 章), 'chinese-section' (CH{N}-1), "
            "'incerto' (Taleb / LaTeX+ArsClassica dispersed-caps). "
            "NOTE: for SCANNED Chinese PDFs, prefer PyMuPDF 2-stage detection "
            "(see feedback_scanned_pdf_workflow.md); pdftotext output of "
            "art-font chapter pages is unreliable."
        ),
    )
    ap.add_argument("--isolate", action="store_true", help="Append PDF md5 suffix to extract_dir")
    ap.add_argument(
        "--select-chapters",
        default=None,
        help=(
            "Optional: only keep numbered chapters matching this spec "
            "(comma-separated, ranges ok, e.g. '1,3,7-9,22-24'). Non-matching "
            "chapter files are deleted after split. Use when distilling only a "
            "subset (e.g. starred ∗ chapters of Taleb's Technical Incerto)."
        ),
    )
    ap.add_argument(
        "--select-appendices",
        default=None,
        help=(
            "Optional: also extract letter-labeled appendices (comma-separated, "
            "case-insensitive letters, e.g. 'A,F,G'). Matches headers like "
            "'F    W H AT A R E...' via a separate regex pass."
        ),
    )
    args = ap.parse_args()

    # Resolve marker regex: explicit --marker-regex wins, else preset
    if args.marker_regex is None:
        args.marker_regex = MARKER_PRESETS[args.preset]

    pdf: Path = args.pdf.expanduser().resolve()
    if not pdf.exists():
        print(f"ERROR: PDF not found: {pdf}", file=sys.stderr)
        sys.exit(1)

    extract_dir = compute_extract_dir(pdf, args.extract_dir.expanduser().resolve(), args.isolate)
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: pdftotext
    full_txt = pdf_to_text(pdf, extract_dir)

    # Step 2: s2twp (optional)
    if not args.no_s2twp:
        opencc_convert(full_txt)

    # Step 3: probe outline
    has_bookmarks = try_pdf_outline(pdf, extract_dir)

    # Step 4: split numbered chapters
    chapters: list[tuple[object, str, int]] = list(
        split_chapters(full_txt, extract_dir, args.marker_regex)
    )

    # Step 4.5: letter-labeled appendices (optional)
    if args.select_appendices:
        appendices = split_appendices(
            full_txt, extract_dir, args.select_appendices.split(",")
        )
        chapters.extend(appendices)

    # Step 4.6: subset filter on numbered chapters
    if args.select_chapters:
        wanted = parse_chapter_selection(args.select_chapters)
        kept: list[tuple[object, str, int]] = []
        for num, fname, size in chapters:
            # letter appendices use str ID, keep unconditionally
            if isinstance(num, str):
                kept.append((num, fname, size))
                continue
            if num in wanted:
                kept.append((num, fname, size))
            else:
                # delete unwanted chapter file from disk
                p = extract_dir / fname
                if p.exists():
                    p.unlink()
        chapters = kept

    # stdout parsable output
    print(f"EXTRACT_DIR={extract_dir}")
    print(f"CHAPTER_COUNT={len(chapters)}")
    chapters_tuples = [
        (n, f, round(s / 1024, 1)) for n, f, s in chapters
    ]
    print(f"CHAPTERS={chapters_tuples}")
    print(f"BOOKMARKS={'true' if has_bookmarks else 'false'}")
    if has_bookmarks:
        print(f"OUTLINE_PATH={extract_dir / 'outline.txt'}")

    # readable summary
    print("\n=== Summary ===", file=sys.stderr)
    print(f"Extracted: {len(chapters)} chapters to {extract_dir}", file=sys.stderr)
    for n, f, kb in chapters_tuples:
        flag = "<15KB (main agent)" if kb < 15 else "≥15KB (subagent)"
        label = f"ch{n:02d}" if isinstance(n, int) else f"app{n}"
        print(f"  {label}: {f}  {kb:>6.1f} KB  {flag}", file=sys.stderr)
    if has_bookmarks:
        print(f"Bookmarks: saved to {extract_dir / 'outline.txt'}", file=sys.stderr)
    else:
        print(
            "Bookmarks: NOT available (chapter titles must be inferred from content)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

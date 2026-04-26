"""Extract text content from epub files by chapter.

Usage:
    uv run python3 epub_extract.py <epub_path> <output_dir> [mode] [--isolate]

Examples:
    # Show OPF metadata (author/title/date/language) — do this BEFORE probe when author unknown
    uv run python3 epub_extract.py book.epub - --show-opf

    # List all chapters (structure scan)
    uv run python3 epub_extract.py book.epub /tmp/out --list

    # Group small sub-chapters into big chapters by heading pattern (Chinese: 第X章, English: Chapter X)
    # Outputs JSON mapping big-chapter-N -> [sub-chapter txt filenames] for subagent dispatch
    uv run python3 epub_extract.py book.epub /tmp/out --group-by-heading

    # Extract specific chapters (e.g., chapters 1-3)
    uv run python3 epub_extract.py book.epub /tmp/out --chapters 1-3

    # Extract all chapters
    uv run python3 epub_extract.py book.epub /tmp/out --all

    # Session-isolated extraction (recommended for distill workflow):
    # appends _<md5(epub)[:8]> to output_dir so parallel sessions never overwrite each other.
    # stdout prints EXTRACT_DIR=<actual_path> for the caller to capture.
    uv run python3 epub_extract.py book.epub author/_tmp_extract --all --isolate
"""

import sys
import os
import re
import html
import hashlib
import zipfile
from pathlib import Path

try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


def get_opf_metadata(z: zipfile.ZipFile) -> dict[str, list[str]]:
    """Extract Dublin Core metadata from OPF (dc:creator, dc:title, dc:date, dc:language, dc:publisher).

    Returns dict with list values (creators/titles can be multi-valued per EPUB spec).
    """
    # Locate OPF file via container.xml
    container = z.read('META-INF/container.xml').decode('utf-8')
    opf_match = re.search(r'full-path="([^"]+)"', container)
    if not opf_match:
        raise ValueError("Cannot find OPF file in container.xml")
    opf_path = opf_match.group(1)
    opf_content = z.read(opf_path).decode('utf-8')

    metadata = {
        'creator': [],
        'title': [],
        'date': [],
        'language': [],
        'publisher': [],
        'identifier': [],
    }

    # Parse <dc:creator>, <dc:title>, etc. — tag may appear with or without namespace prefix
    for key in metadata:
        # Match both <dc:creator ...>text</dc:creator> and <creator ...>text</creator>
        pattern = rf'<(?:dc:)?{key}(?:\s[^>]*)?>([^<]+)</(?:dc:)?{key}>'
        for m in re.finditer(pattern, opf_content):
            value = html.unescape(m.group(1).strip())
            if value and value not in metadata[key]:
                metadata[key].append(value)

    metadata['_opf_path'] = opf_path
    return metadata


def print_opf_metadata(meta: dict) -> None:
    """Print OPF metadata in a parse-friendly format for preflight."""
    print(f"OPF_PATH={meta.get('_opf_path', '')}")
    for key in ('title', 'creator', 'date', 'language', 'publisher', 'identifier'):
        values = meta.get(key, [])
        if values:
            for v in values:
                print(f"{key.upper()}={v}")
        else:
            print(f"{key.upper()}=")


def compute_epub_hash(epub_path: str) -> str:
    """Return first 8 hex chars of md5(epub bytes). Used by --isolate for session-safe tmp dirs."""
    h = hashlib.md5()
    with open(epub_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:8]


def get_spine_order(z: zipfile.ZipFile) -> list[str]:
    """Get ordered list of content files from OPF spine."""
    # Find OPF file
    container = z.read('META-INF/container.xml').decode('utf-8')
    opf_match = re.search(r'full-path="([^"]+)"', container)
    if not opf_match:
        raise ValueError("Cannot find OPF file in container.xml")
    opf_path = opf_match.group(1)
    opf_dir = os.path.dirname(opf_path)

    opf_content = z.read(opf_path).decode('utf-8')

    # Parse manifest: id -> href (handle any attribute order)
    from urllib.parse import unquote
    manifest = {}
    for m in re.finditer(r'<item\s+([^>]*?)/?>', opf_content):
        attrs = m.group(1)
        id_m = re.search(r'id="([^"]*)"', attrs)
        href_m = re.search(r'href="([^"]*)"', attrs)
        if id_m and href_m:
            manifest[id_m.group(1)] = unquote(href_m.group(1))

    # Parse spine order
    spine_ids = re.findall(r'<itemref\s+idref="([^"]*)"', opf_content)

    # Build ordered file list
    ordered_files = []
    for sid in spine_ids:
        if sid in manifest:
            href = manifest[sid]
            # Resolve relative path
            if opf_dir:
                full_path = f"{opf_dir}/{href}"
            else:
                full_path = href
            ordered_files.append(full_path)

    return ordered_files


def get_toc_titles(z: zipfile.ZipFile) -> dict[str, str]:
    """Get chapter titles from NCX TOC."""
    titles = {}
    # Try to find toc.ncx
    for name in z.namelist():
        if name.endswith('toc.ncx'):
            toc_content = z.read(name).decode('utf-8')
            # Extract navPoint text and src pairs
            from urllib.parse import unquote as _unquote
            for nav in re.finditer(
                r'<navPoint[^>]*>.*?<text>([^<]+)</text>.*?<content\s+src="([^"]*)"',
                toc_content, re.DOTALL
            ):
                text = nav.group(1).strip()
                src = nav.group(2).strip()
                # URL-decode and remove fragment
                src = _unquote(src).split('#')[0]
                # Normalize path
                toc_dir = os.path.dirname(name)
                if toc_dir:
                    full_src = f"{toc_dir}/{src}"
                else:
                    full_src = src
                titles[full_src] = text
            break
    return titles


def extract_text(z: zipfile.ZipFile, filepath: str) -> str:
    """Extract plain text from an XHTML file."""
    try:
        raw = z.read(filepath).decode('utf-8')
    except KeyError:
        return ""

    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', raw)
    text = html.unescape(text)

    # Clean whitespace
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return '\n'.join(lines)


def get_html_files_fallback(z: zipfile.ZipFile) -> list[str]:
    """Fallback: get all HTML/XHTML files from zip, sorted by name."""
    html_files = sorted([
        f for f in z.namelist()
        if f.endswith(('.html', '.xhtml', '.htm'))
        and 'toc' not in f.lower()
        and 'nav' not in f.lower()
    ])
    return html_files


def main():
    # Extract --isolate flag before positional arg parsing so it can appear anywhere.
    isolate = '--isolate' in sys.argv
    if isolate:
        sys.argv = [a for a in sys.argv if a != '--isolate']

    # Extract --skip-tail-epigraphs flag: drops trailing chapters whose title is "(untitled-N)".
    # Common pattern: anna's archive epubs append per-Part epigraph collections (each Part's
    # opening quotes consolidated into a separate file) at the end, with no TOC entry, hence
    # the (untitled-N) titles. Skipping them avoids extracting reference quote content that
    # would otherwise be redundant with the main chapters.
    skip_tail_epigraphs = '--skip-tail-epigraphs' in sys.argv
    if skip_tail_epigraphs:
        sys.argv = [a for a in sys.argv if a != '--skip-tail-epigraphs']

    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    epub_path = sys.argv[1]
    output_dir = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else '--all'

    # --isolate: append epub hash to output_dir so parallel sessions never collide on the same path.
    # Skip when output_dir is "-" (stdout-only modes like --show-opf/--list/--group-by-heading).
    if isolate and output_dir != '-':
        ep_hash = compute_epub_hash(epub_path)
        output_dir = f"{output_dir.rstrip('/')}_{ep_hash}"
        print(f"EXTRACT_DIR={output_dir}", flush=True)

    z = zipfile.ZipFile(epub_path)

    # --show-opf: print Dublin Core metadata and exit (preflight step for unknown-author epubs)
    if mode == '--show-opf':
        try:
            meta = get_opf_metadata(z)
            print(f"EPUB: {epub_path}")
            print_opf_metadata(meta)
            sys.exit(0)
        except (ValueError, KeyError) as e:
            print(f"ERROR: Cannot read OPF metadata: {e}", file=sys.stderr)
            sys.exit(2)

    # Get ordered file list and titles
    try:
        spine_files = get_spine_order(z)
    except (ValueError, KeyError):
        spine_files = []
    toc_titles = get_toc_titles(z)

    # Fallback: if spine parsing failed, scan all HTML files in zip
    if not spine_files:
        spine_files = get_html_files_fallback(z)
        if spine_files:
            print(f"[fallback] Spine parsing returned 0 files, scanning zip for HTML: found {len(spine_files)}")

    # Build chapter list with titles
    chapters = []
    for i, filepath in enumerate(spine_files):
        title = toc_titles.get(filepath, f"(untitled-{i})")
        text = extract_text(z, filepath)
        if text.strip():
            chapters.append({
                'index': len(chapters),
                'file': filepath,
                'title': title,
                'text': text,
                'size': len(text.encode('utf-8'))
            })

    # --skip-tail-epigraphs: drop trailing untitled chapters before any mode processes `chapters`.
    # We preserve original `index` values on each chapter so filename generation stays stable.
    if skip_tail_epigraphs:
        skipped_count = 0
        while chapters and chapters[-1]['title'].startswith('(untitled-'):
            chapters.pop()
            skipped_count += 1
        if skipped_count:
            print(f"[skip-tail-epigraphs] Skipped {skipped_count} trailing untitled chapter(s)", file=sys.stderr)

    if mode == '--list':
        print(f"EPUB: {epub_path}")
        print(f"Total chapters: {len(chapters)}")
        print(f"{'#':>3}  {'Size':>8}  Title")
        print("-" * 60)
        for ch in chapters:
            print(f"{ch['index']:>3}  {ch['size']:>8}  {ch['title']}")
        sys.exit(0)

    if mode == '--group-by-heading':
        # Group small sub-chapters into big chapters by heading pattern.
        # Detects: Chinese "第X章" / English "Chapter X" / "Part X" as big-chapter boundaries.
        # Outputs JSON: big_chapters[] with ch#, title, files[], indices[], total_size.
        # Typical use: after --all, dispatch one subagent per big chapter.
        import json

        ch_pattern_cn = re.compile(r'^第[一二三四五六七八九十百千萬\d]+[章回卷部]')
        ch_pattern_en = re.compile(r'^Chapter\s+\d+', re.IGNORECASE)
        ch_pattern_part = re.compile(r'^Part\s+[IVXLCDM\d]+', re.IGNORECASE)

        def make_filename(ch):
            return f"ch{ch['index']:03d}_{re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '_', ch['title'])[:50]}.txt"

        big_chapters = []
        current = None
        big_seq = 0  # independent big-chapter counter; front matter stays at ch=0

        for ch in chapters:
            title = ch['title']
            is_head = (ch_pattern_cn.match(title) or
                       ch_pattern_en.match(title) or
                       ch_pattern_part.match(title))
            filename = make_filename(ch)

            if is_head:
                if current:
                    big_chapters.append(current)
                big_seq += 1
                current = {
                    'ch': big_seq,
                    'title': title,
                    'files': [filename],
                    'indices': [ch['index']],
                    'total_size': ch['size'],
                }
            else:
                if current is None:
                    current = {
                        'ch': 0,
                        'title': '前置內容（cover/TOC/前言等）',
                        'files': [filename],
                        'indices': [ch['index']],
                        'total_size': ch['size'],
                    }
                else:
                    current['files'].append(filename)
                    current['indices'].append(ch['index'])
                    current['total_size'] += ch['size']

        if current:
            big_chapters.append(current)

        # Heuristic: if only 1 big_chapter detected (and it's ch=0 front matter),
        # the heading pattern didn't match — emit a warning.
        detected_heads = sum(1 for bc in big_chapters if bc['ch'] >= 1)
        if detected_heads == 0:
            print("WARNING: No chapter headings detected. "
                  "Check if this book uses non-standard heading (e.g., 'Prologue', "
                  "numbered only like '01', '02', or content files lack title text). "
                  "Falling back to single-group output.", file=sys.stderr)

        print(json.dumps({
            'epub': epub_path,
            'total_sub_chapters': len(chapters),
            'detected_big_chapters': detected_heads,
            'big_chapters': big_chapters,
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    # Determine which chapters to extract
    if mode == '--all':
        selected = chapters
    elif mode.startswith('--chapters'):
        range_str = sys.argv[4] if len(sys.argv) > 4 else mode.split('=')[1] if '=' in mode else ''
        if not range_str and len(sys.argv) > 4:
            range_str = sys.argv[4]
        if '-' in range_str:
            start, end = map(int, range_str.split('-'))
            selected = [ch for ch in chapters if start <= ch['index'] <= end]
        else:
            idx = int(range_str)
            selected = [ch for ch in chapters if ch['index'] == idx]
    else:
        selected = chapters

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Write each chapter to a separate file
    for ch in selected:
        filename = f"ch{ch['index']:03d}_{re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '_', ch['title'])[:50]}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"=== {ch['title']} ===\n\n")
            f.write(ch['text'])
            f.write('\n')
        print(f"[{ch['index']:>3}] {ch['size']:>8} bytes -> {filename}")

    print(f"\nExtracted {len(selected)} chapters to {output_dir}")


if __name__ == '__main__':
    main()

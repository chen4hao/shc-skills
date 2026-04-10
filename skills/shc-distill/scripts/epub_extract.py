"""Extract text content from epub files by chapter.

Usage:
    uv run python3 epub_extract.py <epub_path> <output_dir> [--chapters START-END]

Examples:
    # List all chapters (structure scan)
    uv run python3 epub_extract.py book.epub /tmp/out --list

    # Extract specific chapters (e.g., chapters 1-3)
    uv run python3 epub_extract.py book.epub /tmp/out --chapters 1-3

    # Extract all chapters
    uv run python3 epub_extract.py book.epub /tmp/out --all
"""

import sys
import os
import re
import html
import zipfile
from pathlib import Path

try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


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
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    epub_path = sys.argv[1]
    output_dir = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else '--all'

    z = zipfile.ZipFile(epub_path)

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

    if mode == '--list':
        print(f"EPUB: {epub_path}")
        print(f"Total chapters: {len(chapters)}")
        print(f"{'#':>3}  {'Size':>8}  Title")
        print("-" * 60)
        for ch in chapters:
            print(f"{ch['index']:>3}  {ch['size']:>8}  {ch['title']}")
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

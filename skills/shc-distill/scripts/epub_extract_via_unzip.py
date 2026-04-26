"""Fallback epub extractor using the system `unzip` binary.

Purpose: some epubs (especially re-packaged ones from anna's archive / Library
Genesis) have ZIP headers that Python's stdlib `zipfile` rejects with
`BadZipFile: Bad magic number` even though the `unzip` command line tool can
read them. This script wraps `unzip -p` to provide the same interface as
`epub_extract.py` (--show-opf / --list / --all / --chapters / --isolate) so
the distill pipeline can recover without touching the main tool.

Usage: identical to epub_extract.py, e.g.
    uv run python3 epub_extract_via_unzip.py book.epub author/_tmp_extract --all --isolate
"""

import subprocess
import sys
import os
import re
import html
import hashlib
from urllib.parse import unquote


def unzip_list(epub_path: str) -> list[str]:
    result = subprocess.run(
        ['unzip', '-Z', '-1', epub_path],
        check=True, capture_output=True, text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def unzip_read(epub_path: str, member: str) -> str:
    result = subprocess.run(
        ['unzip', '-p', epub_path, member],
        check=True, capture_output=True,
    )
    return result.stdout.decode('utf-8', errors='replace')


def compute_epub_hash(epub_path: str) -> str:
    h = hashlib.md5()
    with open(epub_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:8]


def locate_opf(epub_path: str, names: list[str]) -> str:
    container_member = next((n for n in names if n.endswith('META-INF/container.xml')), None)
    if not container_member:
        raise ValueError("Cannot find META-INF/container.xml")
    container = unzip_read(epub_path, container_member)
    m = re.search(r'full-path="([^"]+)"', container)
    if not m:
        raise ValueError("Cannot find OPF full-path in container.xml")
    return m.group(1)


def get_opf_metadata(epub_path: str, opf_content: str, opf_path: str) -> dict:
    meta = {'creator': [], 'title': [], 'date': [], 'language': [],
            'publisher': [], 'identifier': []}
    for key in meta:
        pattern = rf'<(?:dc:)?{key}(?:\s[^>]*)?>([^<]+)</(?:dc:)?{key}>'
        for m in re.finditer(pattern, opf_content):
            value = html.unescape(m.group(1).strip())
            if value and value not in meta[key]:
                meta[key].append(value)
    meta['_opf_path'] = opf_path
    return meta


def print_opf_metadata(meta: dict) -> None:
    print(f"OPF_PATH={meta.get('_opf_path', '')}")
    for key in ('title', 'creator', 'date', 'language', 'publisher', 'identifier'):
        values = meta.get(key, [])
        if values:
            for v in values:
                print(f"{key.upper()}={v}")
        else:
            print(f"{key.upper()}=")


def get_spine(opf_content: str, opf_dir: str) -> list[str]:
    manifest = {}
    for m in re.finditer(r'<item\s+([^>]*?)/?>', opf_content):
        attrs = m.group(1)
        id_m = re.search(r'id="([^"]*)"', attrs)
        href_m = re.search(r'href="([^"]*)"', attrs)
        if id_m and href_m:
            manifest[id_m.group(1)] = unquote(href_m.group(1))
    spine_ids = re.findall(r'<itemref\s+idref="([^"]*)"', opf_content)
    ordered = []
    for sid in spine_ids:
        if sid in manifest:
            href = manifest[sid]
            full = f"{opf_dir}/{href}" if opf_dir else href
            ordered.append(full)
    return ordered


def get_toc_titles(epub_path: str, names: list[str]) -> dict[str, str]:
    titles = {}
    ncx_name = next((n for n in names if n.endswith('toc.ncx')), None)
    if not ncx_name:
        return titles
    toc = unzip_read(epub_path, ncx_name)
    toc_dir = os.path.dirname(ncx_name)
    for m in re.finditer(
        r'<navPoint[^>]*>.*?<text>([^<]+)</text>.*?<content\s+src="([^"]*)"',
        toc, re.DOTALL
    ):
        text = html.unescape(m.group(1).strip())
        src = unquote(m.group(2).strip()).split('#')[0]
        full = f"{toc_dir}/{src}" if toc_dir else src
        if full not in titles:
            titles[full] = text
    return titles


def xhtml_to_text(raw: str) -> str:
    raw = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r'<(br|p|div|h[1-6]|li|blockquote|tr)\b[^>]*>', '\n', raw, flags=re.IGNORECASE)
    raw = re.sub(r'</(p|div|h[1-6]|li|blockquote|tr)>', '\n', raw, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', raw)
    text = html.unescape(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return '\n'.join(lines)


def main():
    isolate = '--isolate' in sys.argv
    if isolate:
        sys.argv = [a for a in sys.argv if a != '--isolate']

    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    epub_path = sys.argv[1]
    output_dir = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else '--all'

    if isolate and output_dir != '-':
        ep_hash = compute_epub_hash(epub_path)
        output_dir = f"{output_dir.rstrip('/')}_{ep_hash}"
        print(f"EXTRACT_DIR={output_dir}", flush=True)

    names = unzip_list(epub_path)
    opf_path = locate_opf(epub_path, names)
    opf_content = unzip_read(epub_path, opf_path)
    opf_dir = os.path.dirname(opf_path)

    if mode == '--show-opf':
        meta = get_opf_metadata(epub_path, opf_content, opf_path)
        print(f"EPUB: {epub_path}")
        print_opf_metadata(meta)
        sys.exit(0)

    spine_files = get_spine(opf_content, opf_dir)
    toc_titles = get_toc_titles(epub_path, names)

    chapters = []
    for i, filepath in enumerate(spine_files):
        try:
            raw = unzip_read(epub_path, filepath)
        except subprocess.CalledProcessError:
            continue
        text = xhtml_to_text(raw)
        title = toc_titles.get(filepath, f"(untitled-{i})")
        if text.strip():
            chapters.append({
                'index': len(chapters),
                'file': filepath,
                'title': title,
                'text': text,
                'size': len(text.encode('utf-8')),
            })

    if mode == '--list':
        print(f"EPUB: {epub_path}")
        print(f"Total chapters: {len(chapters)}")
        print(f"{'#':>3}  {'Size':>8}  Title")
        print('-' * 60)
        for ch in chapters:
            print(f"{ch['index']:>3}  {ch['size']:>8}  {ch['title']}")
        sys.exit(0)

    if mode == '--all':
        selected = chapters
    elif mode.startswith('--chapters'):
        range_str = sys.argv[4] if len(sys.argv) > 4 else ''
        if '-' in range_str:
            start, end = map(int, range_str.split('-'))
            selected = [c for c in chapters if start <= c['index'] <= end]
        else:
            idx = int(range_str)
            selected = [c for c in chapters if c['index'] == idx]
    else:
        selected = chapters

    os.makedirs(output_dir, exist_ok=True)
    for ch in selected:
        filename = f"ch{ch['index']:03d}_{re.sub(r'[^a-zA-Z0-9一-鿿]+', '_', ch['title'])[:50]}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"=== {ch['title']} ===\n\n")
            f.write(ch['text'])
            f.write('\n')
        print(f"[{ch['index']:>3}] {ch['size']:>8} bytes -> {filename}")
    print(f"\nExtracted {len(selected)} chapters to {output_dir}")


if __name__ == '__main__':
    main()

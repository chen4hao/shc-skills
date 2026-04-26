#!/usr/bin/env python3
"""Fetch an X/Twitter thread via twitter-thread.com mirror and print full text.

Usage:
    uv run python3 fetch_x_thread.py <status_id_or_url> [--out PATH]

Strategy:
- X 平台封鎖 WebFetch（402），twitter-thread.com 把完整 thread 塞在 <meta name="description"> 裡
- WebFetch 的小模型會主動摘要/截斷長 meta description，故用 curl + regex 精確提取
- 輸出純文字（已解 HTML entity）到 stdout 或指定檔
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path


STATUS_ID_RE = re.compile(r"status/(\d+)")
META_DESC_RE = re.compile(
    r'<meta name="description" content="(.+?)"\s*/>',
    re.DOTALL,
)


def resolve_status_id(arg: str) -> str:
    if arg.isdigit():
        return arg
    m = STATUS_ID_RE.search(arg)
    if not m:
        sys.exit(f"ERROR: cannot extract status id from {arg!r}")
    return m.group(1)


def fetch(url: str) -> str:
    result = subprocess.run(
        ["curl", "-sL", "--max-time", "30", url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        sys.exit(f"ERROR: curl failed (rc={result.returncode}) {result.stderr[:200]}")
    return result.stdout


def extract(html_text: str) -> str:
    m = META_DESC_RE.search(html_text)
    if not m:
        sys.exit("ERROR: meta description not found in page")
    raw = m.group(1)
    return html.unescape(raw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="X status id or full URL")
    ap.add_argument("--out", type=Path, help="write to file instead of stdout")
    args = ap.parse_args()

    status_id = resolve_status_id(args.target)
    url = f"https://twitter-thread.com/t/{status_id}"
    text = extract(fetch(url))

    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"OK: wrote {len(text)} chars to {args.out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()

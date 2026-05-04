"""Fetch and parse mp.weixin.qq.com article in one shot.

Usage:
    uv run --with requests --with beautifulsoup4 --with lxml \
        python3 $SCRIPTS/fetch_wx_article.py <URL>

stdout (one KEY=value per line):
    TITLE=...
    AUTHOR=...
    NICKNAME=...
    PUBLISH_DATE=YYYY-MM-DD
    BODY_PATH=/tmp/wx_<hash>.txt
    CHARS=...
    LINES=...

Why this exists: WebFetch on mp.weixin.qq.com always returns the
"environment anomaly verification" page. Manual workflow needs 6+ separate
Bash calls (curl, grep og:title, grep nickname, grep ct, date -r, wc -l,
Python parse). This script consolidates all of that into one command.
"""

import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Safari/605.1.15"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

ZERO_WIDTH_RE = re.compile(r"[​-‏⁠﻿]")


def grab(pattern: str, html: str, default: str = "") -> str:
    m = re.search(pattern, html)
    return m.group(1).strip() if m else default


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: fetch_wx_article.py <URL>", file=sys.stderr)
        return 2

    url = sys.argv[1]
    if "mp.weixin.qq.com" not in url:
        print(
            f"WARN: URL does not look like a WeChat article: {url}",
            file=sys.stderr,
        )

    resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    html = resp.text

    if "环境异常" in html or "完成验证" in html:
        print("ERROR: hit WeChat anti-bot verification page", file=sys.stderr)
        return 3

    title = grab(r'<meta property="og:title" content="([^"]+)"', html) or grab(
        r"var msg_title = '([^']+)'", html
    )
    author = grab(r'<meta name="author" content="([^"]+)"', html)
    nickname = grab(r'var nickname = htmlDecode\("([^"]+)"\)', html) or grab(
        r'var nickname = "([^"]+)"', html
    )
    ct = grab(r'var ct = "(\d+)"', html)
    publish_date = (
        datetime.fromtimestamp(int(ct)).strftime("%Y-%m-%d")
        if ct.isdigit()
        else ""
    )

    soup = BeautifulSoup(html, "lxml")
    content_div = soup.find("div", id="js_content")
    if content_div is None:
        print(
            "ERROR: missing div#js_content (article body not found)",
            file=sys.stderr,
        )
        return 4

    parts: list[str] = []
    for elem in content_div.find_all(
        ["p", "h1", "h2", "h3", "h4", "blockquote", "li"]
    ):
        text = elem.get_text(separator=" ", strip=True)
        if not text:
            continue
        tag = elem.name
        if tag in ("h1", "h2", "h3", "h4"):
            parts.append(f"\n## {text}\n")
        elif tag == "blockquote":
            parts.append(f"> {text}")
        else:
            parts.append(text)

    body = "\n\n".join(parts)
    body = ZERO_WIDTH_RE.sub("", body)

    digest = hashlib.md5(url.encode()).hexdigest()[:10]
    out_path = Path("/tmp") / f"wx_{digest}.txt"
    out_path.write_text(body, encoding="utf-8")

    line_count = body.count("\n") + 1

    print(f"TITLE={title}")
    print(f"AUTHOR={author}")
    print(f"NICKNAME={nickname}")
    print(f"PUBLISH_DATE={publish_date}")
    print(f"BODY_PATH={out_path}")
    print(f"CHARS={len(body)}")
    print(f"LINES={line_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

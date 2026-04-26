"""One-shot DeepLearning.AI course transcript fetcher.

Given a course URL and a Chrome profile email, this script:
  1. Finds the matching Chrome profile via Local State.profile.info_cache
  2. Copies the Cookies SQLite DB to a temp path (Chrome holds WAL lock on the live DB)
  3. Loads all cookies with browser-cookie3 (no domain filter — requests matches per URL)
  4. Fetches the course landing page to discover lesson URL paths
  5. Fetches every lesson page in parallel (ThreadPoolExecutor, max 6 workers)
  6. Extracts captions from __NEXT_DATA__.props.pageProps.captions
  7. Writes per-lesson {NN}-{slug}.txt and a combined all_transcripts.md

Designed to be zero-interactive — no permission prompts, no advisor calls.
Usage:
  uv run --with browser-cookie3 --with requests python3 $SCRIPTS/fetch_dlai_course.py \\
    --url "https://learn.deeplearning.ai/courses/<slug>" \\
    --email steven.chen4hao@gmail.com \\
    --out-dir /tmp/distill-<slug>
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import re
import shutil
import sqlite3
import sys


CHROME_ROOT = pathlib.Path("/Users/chen4hao/Library/Application Support/Google/Chrome")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)


def find_profile_dir(email: str) -> str:
    local_state = json.loads((CHROME_ROOT / "Local State").read_text())
    info_cache = local_state.get("profile", {}).get("info_cache", {})
    for dir_name, info in info_cache.items():
        if info.get("user_name") == email:
            return dir_name
    raise SystemExit(f"ERROR: No Chrome profile with user_name={email!r} in Local State")


def copy_cookies_db(profile_dir: str, work_dir: pathlib.Path) -> pathlib.Path:
    src = CHROME_ROOT / profile_dir / "Cookies"
    if not src.exists():
        src = CHROME_ROOT / profile_dir / "Network" / "Cookies"
    if not src.exists():
        raise SystemExit(f"ERROR: no Cookies DB under profile {profile_dir!r}")
    dst = work_dir / "cookies.sqlite"
    shutil.copy2(src, dst)
    # Sanity: confirm at least one deeplearning.ai row
    conn = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
    n = conn.execute(
        "SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%deeplearning.ai%'"
    ).fetchone()[0]
    conn.close()
    if n == 0:
        raise SystemExit(
            f"ERROR: profile {profile_dir!r} has no deeplearning.ai cookies. "
            "Log in via browser first."
        )
    return dst


def make_session(cookie_db: pathlib.Path):
    import browser_cookie3  # lazy import so --help works without it
    import requests

    cj = browser_cookie3.chrome(cookie_file=str(cookie_db))
    s = requests.Session()
    s.cookies = cj
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return s


def extract_lesson_paths(course_html: str, course_slug: str) -> list[str]:
    pattern = rf"/courses/{re.escape(course_slug)}/lesson/[A-Za-z0-9]+/[A-Za-z0-9_-]+"
    seen: dict[str, int] = {}
    for m in re.finditer(pattern, course_html):
        p = m.group(0)
        if p not in seen:
            seen[p] = m.start()
    return sorted(seen.keys(), key=lambda p: seen[p])


def fetch_lesson(session, base: str, path: str) -> tuple[str, str]:
    """Return (path, html) tuple."""
    r = session.get(base + path, timeout=30, allow_redirects=True)
    return path, r.text


def parse_lesson(idx: int, path: str, html: str) -> dict:
    from bs4 import BeautifulSoup

    slug = path.rsplit("/", 1)[-1]
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    captions = ""
    title = slug.replace("-", " ").title()
    duration = None
    subtitle_urls: dict = {}
    if script and script.string:
        try:
            data = json.loads(script.string)
            pp = data.get("props", {}).get("pageProps", {})
            captions = (pp.get("captions") or "").strip()
            for q in pp.get("trpcState", {}).get("json", {}).get("queries", []):
                d = (q.get("state") or {}).get("data") or {}
                if isinstance(d, dict):
                    if d.get("wpData") and not title:
                        title = d["wpData"].get("title") or title
                    if d.get("video"):
                        duration = d["video"].get("duration") or duration
                        subtitle_urls = d["video"].get("subtitle") or subtitle_urls
        except json.JSONDecodeError:
            pass
    # Also take title from <h1> / <title> as fallback
    if not title or title == slug.replace("-", " ").title():
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True) or title
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()
    return {
        "idx": idx,
        "slug": slug,
        "path": path,
        "title": title,
        "duration_sec": duration,
        "subtitle_urls": subtitle_urls,
        "captions": captions,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="Course landing URL on learn.deeplearning.ai")
    ap.add_argument("--email", required=True, help="Chrome Google account email logged into DL.AI")
    ap.add_argument("--out-dir", required=True, help="Working output directory (will be created)")
    ap.add_argument("--workers", type=int, default=6, help="Parallel lesson fetch workers")
    args = ap.parse_args()

    url = args.url.rstrip("/")
    m = re.search(r"/courses/([A-Za-z0-9_-]+)", url)
    if not m:
        print(f"ERROR: cannot extract course slug from {url}", file=sys.stderr)
        return 2
    course_slug = m.group(1)

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir = out_dir / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Finding Chrome profile for {args.email}")
    profile_dir = find_profile_dir(args.email)
    print(f"      -> profile dir: {profile_dir!r}")

    print(f"[2/5] Copying Cookies DB")
    cookie_db = copy_cookies_db(profile_dir, out_dir)
    print(f"      -> {cookie_db}")

    session = make_session(cookie_db)

    base = "https://learn.deeplearning.ai"
    print(f"[3/5] Fetching course page to discover lesson paths")
    r = session.get(url, timeout=30, allow_redirects=True)
    print(f"      -> status={r.status_code} final_url={r.url} body={len(r.text)} chars")
    if r.status_code >= 400:
        print("ERROR: non-200 on course page; session may be expired", file=sys.stderr)
        return 3
    (out_dir / "course.html").write_text(r.text, encoding="utf-8")

    lesson_paths = extract_lesson_paths(r.text, course_slug)
    print(f"      -> found {len(lesson_paths)} lesson paths")
    (out_dir / "lesson_paths.json").write_text(json.dumps(lesson_paths, indent=2))
    if not lesson_paths:
        print("ERROR: no lesson paths found", file=sys.stderr)
        return 4

    print(f"[4/5] Fetching {len(lesson_paths)} lessons in parallel (workers={args.workers})")
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_lesson, session, base, p): (i, p) for i, p in enumerate(lesson_paths, 1)}
        for fut in concurrent.futures.as_completed(futures):
            idx, path = futures[fut]
            path_got, html = fut.result()
            # Save raw HTML for debugging
            slug = path.rsplit("/", 1)[-1]
            (lessons_dir / f"{idx:02d}-{slug}.html").write_text(html, encoding="utf-8")
            parsed = parse_lesson(idx, path, html)
            results.append(parsed)
            cap_len = len(parsed["captions"])
            print(f"      [{idx:02d}/{len(lesson_paths)}] {slug}: captions={cap_len} chars")

    results.sort(key=lambda x: x["idx"])

    print(f"[5/5] Writing per-lesson txt and combined markdown")
    combined: list[str] = [
        f"# DeepLearning.AI Course Transcript — {course_slug}",
        "",
        "_Extracted via fetch_dlai_course.py from __NEXT_DATA__.props.pageProps.captions_",
        "",
    ]
    for r in results:
        txt_path = lessons_dir / f"{r['idx']:02d}-{r['slug']}.txt"
        txt_path.write_text(
            "\n".join(
                [
                    f"TITLE: {r['title']}",
                    f"SLUG: {r['slug']}",
                    f"URL: {base}{r['path']}",
                    f"DURATION_SEC: {r['duration_sec']}",
                    f"SUBTITLE_VTT: {json.dumps(r['subtitle_urls'])}",
                    "",
                    "CAPTIONS:",
                    r["captions"],
                ]
            ),
            encoding="utf-8",
        )
        combined.append("\n---\n")
        combined.append(f"## Lesson {r['idx']:02d}: {r['title']}")
        combined.append("")
        if r["captions"]:
            combined.append(r["captions"])
        else:
            combined.append("_（此 lesson 無字幕 — 可能是 reading / quiz）_")

    all_md = out_dir / "all_transcripts.md"
    all_md.write_text("\n".join(combined), encoding="utf-8")

    total = sum(len(r["captions"]) for r in results)
    non_empty = sum(1 for r in results if r["captions"])
    print(f"\nDONE  total_caption_chars={total}  non_empty_lessons={non_empty}/{len(results)}")
    print(f"      combined -> {all_md}")
    print(f"      per-lesson -> {lessons_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

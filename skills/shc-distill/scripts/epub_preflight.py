"""One-shot preflight for (possibly corrupted) epub files.

Handles the common anna's archive / Library Genesis re-packaging failure where
Python's `zipfile` module rejects the file but `unzip` / `zip -FF` can recover
it. Chains:

1. `file` -- sanity-check that the path is actually an EPUB
2. `epub_extract.py --show-opf` -- fast path, works for ~95% of epubs
3. If (2) fails: `zip -FF` repair to /tmp/{md5[:8]}-fixed.epub, then retry (2)
4. If still fails: fall back to `epub_extract_via_unzip.py --show-opf`
5. If `zip -FF` reports missing local entries, print them so the caller can
   mark them as known-missing in the final notes.

stdout contract (for the caller to parse):
    PREFLIGHT_STATUS=ok|fixed|unrecoverable
    EPUB_FOR_EXTRACT=<path>           # use this as input for subsequent --all / --chapters
    MISSING_MEMBERS=<comma-separated> # empty if none; only meaningful when status=fixed
    OPF_PATH=...
    TITLE=...
    CREATOR=...
    DATE=...
    LANGUAGE=...
    PUBLISHER=...
    IDENTIFIER=...

Usage:
    uv run python3 epub_preflight.py <epub_path>
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
EXTRACT_PY = SCRIPTS_DIR / "epub_extract.py"
UNZIP_PY = SCRIPTS_DIR / "epub_extract_via_unzip.py"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def md5_head(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def is_epub_file(path: str) -> bool:
    r = run(["file", path])
    return "EPUB" in r.stdout or "Zip archive" in r.stdout


def show_opf(tool: Path, epub: str) -> subprocess.CompletedProcess:
    return run(["uv", "run", "python3", str(tool), epub, "-", "--show-opf"])


def repair_with_zip_ff(src: str, dst: str) -> tuple[bool, list[str]]:
    """Return (success, missing_members)."""
    r = run(["zip", "-FF", src, "--out", dst])
    if r.returncode not in (0, 1, 2):
        return False, []
    missing = re.findall(r"no local entry:\s*(\S+)", r.stdout + r.stderr)
    return Path(dst).exists(), list(dict.fromkeys(missing))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    epub = sys.argv[1]
    if not Path(epub).exists():
        print(f"ERROR: file not found: {epub}", file=sys.stderr)
        sys.exit(2)

    if not is_epub_file(epub):
        print(f"PREFLIGHT_STATUS=unrecoverable")
        print(f"ERROR: `file` does not identify {epub} as EPUB/ZIP", file=sys.stderr)
        sys.exit(3)

    # Step 1: fast path via epub_extract.py
    r = show_opf(EXTRACT_PY, epub)
    if r.returncode == 0:
        print("PREFLIGHT_STATUS=ok")
        print(f"EPUB_FOR_EXTRACT={epub}")
        print("MISSING_MEMBERS=")
        print(r.stdout.strip())
        return

    # Step 2: try zip -FF repair
    fixed_path = f"/tmp/{md5_head(epub)}-fixed.epub"
    ok, missing = repair_with_zip_ff(epub, fixed_path)
    if ok:
        r2 = show_opf(EXTRACT_PY, fixed_path)
        if r2.returncode == 0:
            print("PREFLIGHT_STATUS=fixed")
            print(f"EPUB_FOR_EXTRACT={fixed_path}")
            print(f"MISSING_MEMBERS={','.join(missing)}")
            print(r2.stdout.strip())
            return

        # Step 3: fallback to unzip-based extractor on the repaired file
        if UNZIP_PY.exists():
            r3 = show_opf(UNZIP_PY, fixed_path)
            if r3.returncode == 0:
                print("PREFLIGHT_STATUS=fixed")
                print(f"EPUB_FOR_EXTRACT={fixed_path}")
                print(f"MISSING_MEMBERS={','.join(missing)}")
                print(r3.stdout.strip())
                return

    # Step 4: last resort -- unzip-based extractor on original
    if UNZIP_PY.exists():
        r4 = show_opf(UNZIP_PY, epub)
        if r4.returncode == 0:
            print("PREFLIGHT_STATUS=ok")
            print(f"EPUB_FOR_EXTRACT={epub}")
            print("MISSING_MEMBERS=")
            print(r4.stdout.strip())
            return

    print("PREFLIGHT_STATUS=unrecoverable")
    print(f"ERROR: all preflight chains failed for {epub}", file=sys.stderr)
    sys.exit(4)


if __name__ == "__main__":
    main()

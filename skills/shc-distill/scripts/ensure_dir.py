"""Create directory (and parents) if it doesn't exist. Usage: ensure_dir.py <path>"""
import os, sys

if len(sys.argv) < 2:
    print("Usage: ensure_dir.py <path>", file=sys.stderr)
    sys.exit(1)

path = sys.argv[1]
os.makedirs(path, exist_ok=True)
print(f"OK: {path}")

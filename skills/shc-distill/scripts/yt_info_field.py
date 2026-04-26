#!/usr/bin/env python3
"""Extract specific fields from yt-dlp info.json without Read-ing the whole file.

yt-dlp info.json contains base64-embedded thumbnails (typically 400K+ tokens),
making it un-Readable via the Read tool even with small limits. This script
parses the JSON and prints only the requested fields.

Usage:
    uv run python3 yt_info_field.py <info.json path> <field1> [field2] ...

Common fields:
    title, description, upload_date, duration, chapters, tags,
    uploader, channel, channel_url, webpage_url, categories

Examples:
    uv run python3 yt_info_field.py /tmp/distill-XXX/XXX.info.json description
    uv run python3 yt_info_field.py /tmp/distill-XXX/XXX.info.json chapters tags
"""
import json
import sys


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: yt_info_field.py <info.json path> <field1> [field2] ...",
            file=sys.stderr,
        )
        sys.exit(1)

    info_path = sys.argv[1]
    fields = sys.argv[2:]

    with open(info_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for field in fields:
        print(f"=== {field} ===")
        value = data.get(field)
        if value is None:
            print("(not present)")
        elif isinstance(value, (list, dict)):
            print(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            print(value)
        print()


if __name__ == "__main__":
    main()

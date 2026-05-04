#!/usr/bin/env python3
"""Check for broken in-page anchor links in the built _site/ HTML.

For each HTML file, collect every href="#..." link and every id="..."
attribute. Report any href targets that have no matching id.

Usage:
    python3 check_links.py [--site _site]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

HREF_RE = re.compile(r'href="#([^"]+)"')
ID_RE = re.compile(r'\bid="([^"]+)"')


def check_file(html_path: Path) -> list[str]:
    text = html_path.read_text(encoding="utf-8")
    ids = set(ID_RE.findall(text))
    return sorted(href for href in set(HREF_RE.findall(text)) if href not in ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="_site", help="built site directory (default: _site)")
    args = parser.parse_args()

    site = ROOT / args.site
    if not site.exists():
        print(f"error: {site} not found — run build_site.py first", file=sys.stderr)
        return 1

    total = 0
    for html_path in sorted(site.rglob("*.html")):
        broken = check_file(html_path)
        if broken:
            print(f"{html_path.relative_to(ROOT)}:")
            for b in broken:
                print(f"  missing #{b}")
            total += len(broken)

    if total == 0:
        print("All in-page anchor links are valid.")
        return 0

    print(f"\n{total} broken link(s) total.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

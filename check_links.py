#!/usr/bin/env python3
"""Check for broken anchor links in the built _site/ HTML.

Checks two kinds of fragment links in every HTML file:
  - In-page:     href="#anchor"          — target id must exist in the same file
  - Cross-page:  href="path.html#anchor" — target file must exist and contain the id

Usage:
    python3 check_links.py [--site _site]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# href="#anchor"
INPAGE_RE = re.compile(r'href="#([^"]+)"')
# href="relative/path.html#anchor"  (no scheme, no leading /)
CROSSPAGE_RE = re.compile(r'href="([^"#:/][^"#]*\.html)#([^"]+)"')
ID_RE = re.compile(r'\bid="([^"]+)"')


def _ids(html_path: Path) -> set[str]:
    return set(ID_RE.findall(html_path.read_text(encoding="utf-8")))


def check_file(html_path: Path, id_cache: dict[Path, set[str]]) -> list[str]:
    text = html_path.read_text(encoding="utf-8")
    errors: list[str] = []

    # In-page links
    local_ids = set(ID_RE.findall(text))
    for anchor in set(INPAGE_RE.findall(text)):
        if anchor not in local_ids:
            errors.append(f"missing #{anchor}")

    # Cross-page fragment links
    for rel_path, anchor in set(CROSSPAGE_RE.findall(text)):
        target = (html_path.parent / rel_path).resolve()
        if not target.exists():
            errors.append(f"missing file {rel_path}#{anchor}")
            continue
        if target not in id_cache:
            id_cache[target] = _ids(target)
        if anchor not in id_cache[target]:
            errors.append(f"missing {rel_path}#{anchor}")

    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="_site", help="built site directory (default: _site)")
    args = parser.parse_args()

    site = ROOT / args.site
    if not site.exists():
        print(f"error: {site} not found — run build_site.py first", file=sys.stderr)
        return 1

    id_cache: dict[Path, set[str]] = {}
    total = 0
    for html_path in sorted(site.rglob("*.html")):
        broken = check_file(html_path, id_cache)
        if broken:
            print(f"{html_path.relative_to(ROOT)}:")
            for b in broken:
                print(f"  {b}")
            total += len(broken)

    if total == 0:
        print("All anchor links are valid.")
        return 0

    print(f"\n{total} broken link(s) total.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

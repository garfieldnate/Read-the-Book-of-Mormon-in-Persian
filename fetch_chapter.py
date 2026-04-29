#!/usr/bin/env python3
"""Download a churchofjesuschrist.org Persian-edition scripture page and
emit its structured text.

Pulls the page over HTTPS, parses with the stdlib html parser, and walks
the small set of CSS classes the publisher uses to mark structural
elements:

    h1                  → book title (only on chapter 1 of each book)
    p.subtitle          → book subtitle (only on chapter 1)
    p.intro             → book-level summary (only on chapter 1)
    p.title-number      → "فصل N" — chapter heading
    p.study-summary     → chapter heading paragraph
    p.verse             → individual verse (with leading <span class="verse-number">)

Output is plain text grouped under `# section` headers, one block per
element; useful for hand-authoring `chN.md` for a new chapter without
going through the corruption-prone PDF-extraction pipeline.

Usage:
    python3 fetch_chapter.py <url> [-o output.txt]

Example:
    python3 fetch_chapter.py \\
        https://www.churchofjesuschrist.org/study/scriptures/bofm/1-ne/2?lang=pes \\
        -o 02_nephi/web.txt

No dependencies beyond the Python 3.10+ standard library.
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# A real-browser UA — the church.org CDN sometimes serves a stub to
# unrecognised UAs.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

# Element classes we capture. Each entry is (tag, css-class, output-label).
# `None` for class means "any class — capture by tag". Order is the order
# in which they're emitted in the output.
CAPTURE_RULES = [
    ("h1", None, "title"),
    ("p", "subtitle", "subtitle"),
    ("p", "intro", "intro"),
    ("p", "title-number", "chapter"),
    ("p", "study-summary", "study-summary"),
    ("p", "verse", "verse"),  # repeated; numbered in order of appearance
]


class _Extractor(HTMLParser):
    """Collect text content of selected elements in document order."""

    def __init__(self) -> None:
        super().__init__()
        # When we're inside a captured element, this is the depth at which
        # the element opened. Lets us tolerate nested tags (e.g. <span>
        # inside a <p class="verse">) without losing track.
        self._capture_depth: int | None = None
        self._capture_label: str | None = None
        self._buf: list[str] = []
        self._stack: list[str] = []
        # (label, text) tuples in document order.
        self.records: list[tuple[str, str]] = []

    @staticmethod
    def _label_for(tag: str, classes: list[str]) -> str | None:
        for rule_tag, rule_class, label in CAPTURE_RULES:
            if rule_tag != tag:
                continue
            if rule_class is None or rule_class in classes:
                return label
        return None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack.append(tag)
        if self._capture_depth is not None:
            return
        attr_dict = {k: (v or "") for k, v in attrs}
        classes = attr_dict.get("class", "").split()
        label = self._label_for(tag, classes)
        if label is not None:
            self._capture_depth = len(self._stack) - 1
            self._capture_label = label
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        # Pop the matching tag off the stack (tolerate a nested mismatch).
        if self._stack:
            self._stack.pop()
        if (
            self._capture_depth is not None
            and len(self._stack) == self._capture_depth
        ):
            text = "".join(self._buf)
            text = text.replace("\xa0", " ")
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                assert self._capture_label is not None
                self.records.append((self._capture_label, text))
            self._capture_depth = None
            self._capture_label = None
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._capture_depth is not None:
            self._buf.append(data)

    def handle_entityref(self, name: str) -> None:
        # html.parser normally converts named entities itself, but be
        # defensive in case `convert_charrefs` is False on some platform.
        if self._capture_depth is not None:
            from html import unescape
            self._buf.append(unescape(f"&{name};"))


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=30) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except (HTTPError, URLError) as e:
        raise SystemExit(f"failed to fetch {url}: {e}") from e


def extract(html_text: str) -> list[tuple[str, str]]:
    ex = _Extractor()
    ex.feed(html_text)
    ex.close()
    return ex.records


def format_output(records: list[tuple[str, str]]) -> str:
    """Render captured records as `# section` blocks. Verses are numbered
    in encounter order so the output is grep-friendly."""
    lines: list[str] = []
    verse_n = 0
    for label, text in records:
        if label == "verse":
            verse_n += 1
            header = f"# verse {verse_n}"
        else:
            header = f"# {label}"
        lines.append(header)
        lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="scripture page URL (e.g. https://www.churchofjesuschrist.org/study/scriptures/bofm/1-ne/1?lang=pes)")
    parser.add_argument("-o", "--output", help="write to file instead of stdout")
    args = parser.parse_args()

    html_text = fetch(args.url)
    records = extract(html_text)
    if not records:
        print("warning: no recognised elements found on page", file=sys.stderr)
    output = format_output(records)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"wrote {args.output} ({len(output):,} chars, {len(records)} blocks)", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the static GitHub Pages site for the Persian Book of Mormon study guides.

Walks every chapter directory matching `study_guide/NN_*/chN.md`, renders each
Markdown study guide to HTML using `render.py`, copies `styles.css` next to the
rendered files, and emits a top-level `index.html` linking to each chapter
along with the original publication's title and copyright.

Also renders `study_guide/transcription.md` as a standalone reference page
linked from the index.

Output goes to `./_site/`. Existing contents of `_site/` are wiped first so a
re-run is reproducible.

Usage:
    python3 build_site.py [--out _site]

No dependencies beyond the Python 3.10+ standard library.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import json

from render import render
from render_json import render_chapter

ROOT = Path(__file__).resolve().parent
CHAPTER_DIR_RE = re.compile(r"^(\d+)_([a-z0-9_-]+)$", re.IGNORECASE)
CHAPTER_FILE_RE = re.compile(r"^ch(\d+)\.md$", re.IGNORECASE)

# Original publication metadata, taken from the title and copyright pages of
# `book-of-mormon-59010-pes.pdf` (item 59010-pes, the official Persian
# translation). Pulled out here so the index page can credit the source.
SOURCE_TITLE_FA = "کتاب مورمون"
SOURCE_SUBTITLE_FA = "گواهی دیگری بر عیسی مسیح"
SOURCE_TITLE_EN = "The Book of Mormon — Another Testament of Jesus Christ"
SOURCE_PUBLISHER = "Published by The Church of Jesus Christ of Latter-day Saints, Salt Lake City, Utah, USA"
SOURCE_COPYRIGHT = "© 2015 by Intellectual Reserve, Inc. All rights reserved."
SOURCE_TRANSLATION_NOTE = "Translation of the Book of Mormon — Persian. English approval: 6/13. Translation approval: 6/13."


H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def extract_title(md_text: str, fallback: str) -> str:
    """Pull the first H1 from a markdown file, stripping any "— Persian Study Guide" suffix."""
    m = H1_RE.search(md_text)
    if not m:
        return fallback
    title = m.group(1)
    title = re.split(r"\s+[—–-]\s+Persian\s+Study\s+Guide\b", title)[0].strip()
    return title or fallback


_CHAPTER_STEM_RE = re.compile(r"^ch(\d+)$", re.IGNORECASE)


def _title_from_study_json(study: dict, fallback: str) -> str:
    book = study.get("book", "")
    chapter = study.get("chapter", "")
    if book and chapter:
        return f"{book} {chapter}"
    return fallback


def discover_chapters(root: Path) -> list[tuple[int, str, Path, Path]]:
    """Return (chapter_number, display_title, source_dir, stem_path) for each chapter.

    stem_path has no extension; the build loop appends .source.json/.study.json or .md.
    JSON pairs take priority; .md-only chapters are discovered as a fallback.
    """
    study_guide = root / "study_guide"
    chapters: list[tuple[int, str, Path, Path]] = []
    if not study_guide.is_dir():
        return chapters
    for entry in sorted(study_guide.iterdir()):
        if not entry.is_dir():
            continue
        m = CHAPTER_DIR_RE.match(entry.name)
        if not m:
            continue
        seen: set[int] = set()
        for src_json in sorted(entry.glob("ch*.source.json")):
            stem = src_json.name[: -len(".source.json")]
            cm = _CHAPTER_STEM_RE.match(stem)
            if not cm:
                continue
            stu_json = entry / (stem + ".study.json")
            if not stu_json.exists():
                continue
            ch_num = int(cm.group(1))
            fallback = f"{entry.name} ch{ch_num}"
            study_data = json.loads(stu_json.read_text(encoding="utf-8"))
            title = _title_from_study_json(study_data, fallback)
            chapters.append((ch_num, title, entry, entry / stem))
            seen.add(ch_num)
        for md in sorted(entry.glob("ch*.md")):
            cm = CHAPTER_FILE_RE.match(md.name)
            if not cm:
                continue
            ch_num = int(cm.group(1))
            if ch_num in seen:
                continue
            fallback = f"{entry.name} ch{ch_num}"
            title = extract_title(md.read_text(encoding="utf-8"), fallback)
            chapters.append((ch_num, title, entry, md.with_suffix("")))
            seen.add(ch_num)
    chapters.sort(key=lambda t: (t[2].name, t[0]))
    return chapters


def build_index(
    chapters: list[tuple[int, str, Path, Path]],
    has_transcription: bool = False,
    has_verbs: bool = False,
    has_arabic: bool = False,
) -> str:
    """Render the top-level index.html linking each chapter."""
    items: list[str] = []
    for ch_num, title, src_dir, md_path in chapters:
        href = f"study_guide/{src_dir.name}/{md_path.stem}.html"
        items.append(
            f'    <li><a href="{href}">{title}</a></li>'
        )
    items_html = "\n".join(items) if items else "    <li><em>No chapters yet.</em></li>"

    ref_items: list[str] = []
    if has_transcription:
        ref_items.append('    <li><a href="study_guide/transcription.html">Persian Transliteration Scheme</a></li>')
    if has_verbs:
        ref_items.append('    <li><a href="study_guide/verbs.html">Persian Verb Conjugations</a></li>')
    if has_arabic:
        ref_items.append('    <li><a href="study_guide/arabic.html">Arabic Borrowings in Persian</a></li>')

    transcription_section = ""
    if ref_items:
        transcription_section = (
            "\n<h2>Reference</h2>\n<ul class=\"chapter-list\">\n"
            + "\n".join(ref_items)
            + "\n</ul>\n"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Persian Book of Mormon — Study Guides</title>
<link rel="stylesheet" href="study_guide/styles.css">
<style>
  .source-credit {{
    margin: 2em 0;
    padding: 1em 1.2em;
    border-left: 4px solid var(--rule);
    background: var(--meta-bg);
    border-radius: 0 4px 4px 0;
    font-size: 0.95em;
    line-height: 1.55;
  }}
  .source-credit .fa {{
    font-family: var(--font-fa);
    font-size: 1.25em;
    color: var(--persian-color);
    direction: rtl;
    text-align: right;
    display: block;
    margin: 0.2em 0;
  }}
  .source-credit p {{ margin: 0.4em 0; }}
  .chapter-list {{ list-style: none; padding: 0; margin: 1.5em 0; }}
  .chapter-list li {{
    margin: 0.5em 0;
    padding: 0.4em 0.8em;
    border-bottom: 1px solid #e3dcc6;
  }}
  .chapter-list a {{
    text-decoration: none;
    color: var(--accent);
    font-size: 1.15em;
  }}
  .chapter-list a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<main>
<h1>Persian Book of Mormon — Study Guides</h1>

<p>Learner-oriented English study guides for the Persian translation of the
Book of Mormon. Each chapter has a vocabulary section (every distinct lemma,
grouped by verse) and a grammar section (10–12 tricky points with verbatim
examples).</p>

{transcription_section}<h2>Chapters</h2>
<ul class="chapter-list">
{items_html}
</ul>

<h2>Source publication</h2>
<div class="source-credit">
  <span class="fa">{SOURCE_TITLE_FA}</span>
  <span class="fa">{SOURCE_SUBTITLE_FA}</span>
  <p><strong>{SOURCE_TITLE_EN}</strong></p>
  <p>{SOURCE_PUBLISHER}</p>
  <p>{SOURCE_COPYRIGHT}</p>
  <p><em>{SOURCE_TRANSLATION_NOTE}</em></p>
</div>

<p style="font-size:0.9em;color:var(--text-muted);">
  These study guides quote the Persian translation of the Book of Mormon for
  educational and personal-study purposes; all rights to the source text remain
  with the copyright holder.
</p>
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="_site", help="output directory (default: _site)")
    args = parser.parse_args()

    out_dir = ROOT / args.out
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Copy stylesheet into _site/study_guide/ so chapter pages find it at ../styles.css
    # and the index links to it at study_guide/styles.css.
    sg_css_dir = out_dir / "study_guide"
    sg_css_dir.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "study_guide" / "styles.css", sg_css_dir / "styles.css")

    chapters = discover_chapters(ROOT)
    if not chapters:
        print("warning: no chapters found (looking for study_guide/NN_*/chN.md)", file=sys.stderr)

    sg_out_dir = out_dir / "study_guide"
    sg_out_dir.mkdir(exist_ok=True)

    # Each entry: (out_html_path, display_title, source_md, css_href, source_name)
    # Order matches the index page: reference pages first, then chapters.
    Page = tuple[Path, str, Path, str, str]
    all_pages: list[Page] = []

    transcription_md = ROOT / "study_guide" / "transcription.md"
    has_transcription = transcription_md.exists()
    if has_transcription:
        all_pages.append((
            sg_out_dir / "transcription.html",
            "Persian Transliteration Scheme",
            transcription_md.with_suffix(""),
            "styles.css",
            "study_guide/transcription.md",
        ))

    verbs_md = ROOT / "study_guide" / "verbs.md"
    has_verbs = verbs_md.exists()
    if has_verbs:
        all_pages.append((
            sg_out_dir / "verbs.html",
            "Persian Verb Conjugations",
            verbs_md.with_suffix(""),
            "styles.css",
            "study_guide/verbs.md",
        ))

    arabic_md = ROOT / "study_guide" / "arabic.md"
    has_arabic = arabic_md.exists()
    if has_arabic:
        all_pages.append((
            sg_out_dir / "arabic.html",
            "Arabic Borrowings in Persian",
            arabic_md.with_suffix(""),
            "styles.css",
            "study_guide/arabic.md",
        ))

    for ch_num, title, src_dir, stem_path in chapters:
        ch_out_dir = out_dir / "study_guide" / src_dir.name
        ch_out_dir.mkdir(parents=True, exist_ok=True)
        src_json = stem_path.parent / (stem_path.name + ".source.json")
        if src_json.exists():
            source_name = str(src_json.relative_to(ROOT))
        else:
            source_name = str((stem_path.parent / (stem_path.name + ".md")).relative_to(ROOT))
        all_pages.append((
            ch_out_dir / (stem_path.name + ".html"),
            title,
            stem_path,
            "../styles.css",
            source_name,
        ))

    def _sibling_href(from_path: Path, to_path: Path) -> str:
        return os.path.relpath(to_path, from_path.parent)

    for i, (html_path, title, stem_path, css_href, source_name) in enumerate(all_pages):
        prev = (
            (_sibling_href(html_path, all_pages[i - 1][0]), all_pages[i - 1][1])
            if i > 0 else None
        )
        next_ = (
            (_sibling_href(html_path, all_pages[i + 1][0]), all_pages[i + 1][1])
            if i < len(all_pages) - 1 else None
        )
        src_json = stem_path.parent / (stem_path.name + ".source.json")
        stu_json = stem_path.parent / (stem_path.name + ".study.json")
        if src_json.exists() and stu_json.exists():
            source_data = json.loads(src_json.read_text(encoding="utf-8"))
            study_data  = json.loads(stu_json.read_text(encoding="utf-8"))
            html = render_chapter(
                source_data, study_data,
                css_href=css_href, source_name=source_name, prev=prev, next=next_,
            )
            print(f"  {src_json.relative_to(ROOT)} → {html_path.relative_to(ROOT)} [json]", file=sys.stderr)
        else:
            md_file = stem_path.parent / (stem_path.name + ".md")
            md_text = md_file.read_text(encoding="utf-8")
            html = render(md_text, css_href=css_href, source_name=source_name, prev=prev, next=next_)
            print(f"  {md_file.relative_to(ROOT)} → {html_path.relative_to(ROOT)}", file=sys.stderr)
        html_path.write_text(html, encoding="utf-8")

    index_path = out_dir / "index.html"
    index_path.write_text(
        build_index(chapters, has_transcription=has_transcription, has_verbs=has_verbs, has_arabic=has_arabic),
        encoding="utf-8",
    )
    print(f"  index → {index_path.relative_to(ROOT)} ({len(chapters)} chapter(s))", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

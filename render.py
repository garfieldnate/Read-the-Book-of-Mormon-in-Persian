#!/usr/bin/env python3
"""Render a chapter study guide from Markdown to semantic HTML.

Converts a chapter's Markdown study guide into an HTML file with a small,
documented set of CSS classes applied to the semantically meaningful
elements (vocab entries, grammar examples, Persian text, transliterations,
line references, proper-noun tags). The HTML links to a shared stylesheet
at ../styles.css so every chapter shares one visual identity.

Usage:
    python3 render.py <input.md> <output.html>

Class taxonomy (see README § HTML rendering for details):
    .vocab          <ul> of vocabulary entries
    .vocab-entry    <li> for one vocabulary lemma
    .persian        inline Persian text (RTL, Persian font) — used on the
                    <strong> that opens a vocab entry and on Persian lines
                    in examples
    .translit       transliteration (italic) — used on the <em> that
                    follows the Persian in a vocab entry
    .example        <div> wrapping a grammar example (replaces <blockquote>)
    .example-fa     Persian line inside an example
    .example-tr     transliteration line inside an example
    .example-en     English translation line inside an example
    .line-ref       "Line N:" / "Lines N–M:" citation at the start of an
                    example's Persian line
    .proper         the "[proper]" tag following a proper-noun entry

No dependencies beyond the Python 3.10+ standard library.
"""
from __future__ import annotations

import html as html_lib
import re
import sys
from pathlib import Path


# ---------- inline formatting ----------

def _inline(text: str) -> str:
    """Apply markdown inline formatting (**bold**, *italic*, `code`)."""
    # Escape HTML-special chars first, except we want to preserve backticks
    # and asterisks as-is for the next step.
    text = html_lib.escape(text, quote=False)
    # Backtick code — process first so content inside backticks isn't
    # mis-treated as italic.
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    # Bold before italic so **x** doesn't get eaten by *x*
    text = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    return text


# ---------- post-processing: vocab entries ----------

LINE_REF_RE = re.compile(
    r"^(Lines?\s+[\d–—\-]+:)\s*(.*)$"
)


def _wrap_vocab_entry(content: str) -> str:
    """Inject .persian, .translit, .proper inside a vocab entry."""
    # First <strong> → Persian headword
    content = re.sub(
        r"<strong>([^<]+)</strong>",
        r'<strong class="persian">\1</strong>',
        content,
        count=1,
    )
    # First <em> after that → transliteration
    content = re.sub(
        r"<em>([^<]+)</em>",
        r'<em class="translit">\1</em>',
        content,
        count=1,
    )
    # [proper] tag
    content = content.replace("[proper]", '<span class="proper">[proper]</span>')
    return content


# ---------- post-processing: grammar examples ----------

def _build_example(bq_lines: list[str]) -> str:
    """Take the text (already inline-rendered) of consecutive blockquote lines
    and emit a <div class="example"> with semantically-classed children."""
    line_classes = ["example-fa", "example-tr", "example-en"]
    out: list[str] = ['<div class="example">']
    for i, line in enumerate(bq_lines):
        cls = line_classes[i] if i < len(line_classes) else "example-en"
        if cls == "example-fa":
            # Extract "Lines N–M:" prefix, if present
            m = LINE_REF_RE.match(line)
            if m:
                ref, rest = m.group(1), m.group(2)
                line = f'<span class="line-ref">{ref}</span> {rest}'
        out.append(f'  <div class="{cls}">{line}</div>')
    out.append("</div>")
    return "\n".join(out)


# ---------- block-level parser ----------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
HR_SET = {"---", "***", "___"}
LIST_RE = re.compile(r"^(\s*)-\s+(.+)$")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")


def _build_tree(
    items: list[tuple[int, str]], start: int, level: int
) -> tuple[list[tuple[str, list]], int]:
    """Build a tree of (content, children) nodes from flat (indent, content) items.

    Returns the list of sibling nodes at `level` plus the index after the last
    one consumed.
    """
    nodes: list[tuple[str, list]] = []
    i = start
    while i < len(items):
        indent, content = items[i]
        if indent < level:
            break
        if indent > level:
            # Stray deeper item without a parent at this level — fold into last node.
            if nodes:
                children, i = _build_tree(items, i, indent)
                prev_content, prev_children = nodes[-1]
                nodes[-1] = (prev_content, prev_children + children)
            else:
                # Orphan deep item: treat as level-level node.
                nodes.append((content, []))
                i += 1
            continue
        # indent == level
        i += 1
        children: list[tuple[str, list]] = []
        if i < len(items) and items[i][0] > level:
            children, i = _build_tree(items, i, items[i][0])
        nodes.append((content, children))
    return nodes, i


def _emit_tree(
    nodes: list[tuple[str, list]], depth: int = 0, is_vocab: bool = False
) -> str:
    """Emit properly-nested HTML from a tree of nodes."""
    sp = "  " * depth
    ul_attr = ' class="vocab"' if is_vocab else ""
    out: list[str] = [f"{sp}<ul{ul_attr}>"]
    for content, children in nodes:
        if is_vocab:
            li_open = '<li class="vocab-entry">'
            li_content = _wrap_vocab_entry(content)
        else:
            li_open = "<li>"
            li_content = content
        if children:
            out.append(f"{sp}  {li_open}{li_content}")
            out.append(_emit_tree(children, depth + 2, is_vocab=False))
            out.append(f"{sp}  </li>")
        else:
            out.append(f"{sp}  {li_open}{li_content}</li>")
    out.append(f"{sp}</ul>")
    return "\n".join(out)


def _emit_list(items: list[tuple[int, str]]) -> str:
    """Render a flat list of (indent_level, html) into nested <ul>/<li>.

    A top-level list whose items all start with <strong> is tagged class="vocab"
    and its items get class="vocab-entry"; sub-lists are always plain.
    """
    top_items_content = [c for indent, c in items if indent == 0]
    top_is_vocab = bool(top_items_content) and all(
        c.startswith("<strong>") for c in top_items_content
    )
    tree, _ = _build_tree(items, 0, 0)
    return _emit_tree(tree, depth=0, is_vocab=top_is_vocab)


def _render_body(md: str) -> str:
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Horizontal rule
        if stripped in HR_SET:
            out.append("<hr>")
            i += 1
            continue

        # Heading
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Blockquote — consume consecutive > lines as a single example
        if BLOCKQUOTE_RE.match(line):
            bq_lines: list[str] = []
            while i < n:
                bq_m = BLOCKQUOTE_RE.match(lines[i])
                if not bq_m:
                    break
                bq_lines.append(_inline(bq_m.group(1).strip()))
                i += 1
            out.append(_build_example(bq_lines))
            continue

        # Unordered list — consume consecutive "- " items (any indent)
        if LIST_RE.match(line):
            items: list[tuple[int, str]] = []
            while i < n:
                m = LIST_RE.match(lines[i])
                if not m:
                    break
                indent = len(m.group(1)) // 2  # 2 spaces per nesting level
                items.append((indent, _inline(m.group(2))))
                i += 1
            out.append(_emit_list(items))
            continue

        # Blank line — skip
        if not stripped:
            i += 1
            continue

        # Paragraph — collect until a block delimiter
        para: list[str] = []
        while i < n:
            pl = lines[i]
            ps = pl.strip()
            if (
                not ps
                or HEADING_RE.match(pl)
                or BLOCKQUOTE_RE.match(pl)
                or LIST_RE.match(pl)
                or ps in HR_SET
            ):
                break
            para.append(ps)
            i += 1
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")

    return "\n".join(out)


# ---------- document skeleton ----------

DOCUMENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def render(md_text: str, css_href: str = "../styles.css") -> str:
    body = _render_body(md_text)
    # Prefer the first H1 as the document title
    m = re.search(r"^#\s+(.+)$", md_text, flags=re.MULTILINE)
    title = _inline(m.group(1)) if m else "Study Guide"
    # Strip any HTML from the title for the <title> element
    plain_title = re.sub(r"<[^>]+>", "", title)
    return DOCUMENT.format(title=plain_title, css=css_href, body=body)


# ---------- CLI ----------

def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <input.md> <output.html>", file=sys.stderr)
        return 2
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    md_text = in_path.read_text(encoding="utf-8")
    html = render(md_text)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({len(html):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

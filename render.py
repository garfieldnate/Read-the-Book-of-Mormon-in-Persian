#!/usr/bin/env python3
"""Render a chapter study guide from Markdown to semantic HTML.

Converts a chapter's Markdown study guide into an HTML file with a small,
documented set of CSS classes applied to the semantically meaningful
elements (vocab entries, grammar examples, Persian text, transliterations,
line references, proper-noun tags). The HTML links to a shared stylesheet
at study_guide/styles.css (default css_href="../styles.css" is relative to each chapter's NN_book/ dir).

Usage:
    python3 render.py <input.md> <output.html>

Class taxonomy (see README § HTML rendering for details):
    .vocab           <ul> of vocabulary entries
    .vocab-entry     <li> for one vocabulary lemma
    .vocab-meta      <ul> nested inside a .vocab-entry; metadata sub-bullets
    .vocab-etym      <li> in .vocab-meta whose label is *Etym* / *Etymology*
    .vocab-forms     <li> in .vocab-meta whose label is *Forms* / *Form*
    .vocab-family    <li> in .vocab-meta whose label is *Family* — related words
    .vocab-meta-other  fallback for an unrecognized meta label
    .meta-label      the leading "Etym" / "Forms" chip of a meta sub-bullet
    .persian         inline Persian text (RTL, Persian font) — used on the
                     <strong> that opens a vocab entry
    .translit        transliteration (italic) — used on the <em> that
                     follows the Persian in a vocab entry
    .example         <div> wrapping a grammar example (replaces <blockquote>)
    .example-fa      Persian line inside an example
    .example-tr      transliteration line inside an example
    .example-en      English translation line inside an example
    .line-ref        "Line N:" / "Lines N–M:" citation at the start of an
                     example's Persian line
    .proper          the "[proper]" tag following a proper-noun entry

No dependencies beyond the Python 3.10+ standard library.
"""
from __future__ import annotations

import html as html_lib
import re
import sys
from pathlib import Path


# ---------- inline formatting ----------

_ESCAPABLE = "*_`\\"

# Matches a leading <span id="...">inner</span> in a table cell, used to
# emit HTML id anchors that survive the normal html.escape() pass.
_CELL_ANCHOR_RE = re.compile(r'^<span\s+id="([^"]+)">(.*?)</span>(.*)', re.DOTALL)


def _slug(text: str) -> str:
    """Convert heading text to a URL-safe id slug."""
    text = re.sub(r"<[^>]+>", "", text)  # strip any HTML tags
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _inline(text: str) -> str:
    """Apply markdown inline formatting (**bold**, *italic*, `code`).

    Honours CommonMark-style backslash escapes for the formatting specials
    (`\\*`, `\\_`, `` \\` ``, `\\\\`) — the escaped char is converted to its
    numeric HTML entity *before* the formatting regexes run, so it can't be
    consumed as the start/end of an emphasis run. The browser still
    displays the entity as the literal character.
    """
    # Escape HTML-special chars first, except we want to preserve backticks
    # and asterisks as-is for the next step.
    text = html_lib.escape(text, quote=False)
    # Backslash-escaped markdown specials → numeric entity, so the
    # subsequent regex passes don't treat them as emphasis delimiters.
    text = re.sub(
        r"\\([" + re.escape(_ESCAPABLE) + r"])",
        lambda m: f"&#{ord(m.group(1))};",
        text,
    )
    # Editorial ezafe marker: `{e}` in markdown → a styled kasra in HTML.
    # The Persian Book of Mormon translation almost never writes the ezafe
    # (-e linker) on consonant-final words; we add it for the reader by
    # inserting `{e}` at the appropriate site in the inline source text or
    # grammar example. The marker becomes a `<span class="ezafe">…</span>`
    # carrying the kasra (U+0650), which is a combining mark that attaches
    # visually to the preceding letter while the wrapping span lets CSS
    # color it distinctly so the reader sees it's an editorial addition.
    text = text.replace("{e}", '<span class="ezafe">ِ</span>')
    # Markdown links [text](url) → <a href="url">text</a>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # Backtick code — process first so content inside backticks isn't
    # mis-treated as italic.
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    # Bold before italic so **x** doesn't get eaten by *x*
    text = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_]+?)_(?!_)", r"<em>\1</em>", text)
    # Wrap runs of 2+ consecutive Persian code spans in an RTL container so
    # multi-word phrases (e.g. `به` `هنگام`) display in the correct reading order.
    text = re.sub(
        r"(<code>[^<]*[؀-ۿ][^<]*</code>(?:[  ]*<code>[^<]*[؀-ۿ][^<]*</code>)+)",
        r'<span dir="rtl">\1</span>',
        text,
    )
    return text


# ---------- vocab map: first-pass word → anchor-id lookup ----------

_PERSIAN_CHAR_RE = re.compile(r"[؀-ۿ‌]")
_PERSIAN_TOKEN_RE = re.compile(r"[ء-ۿ‌]+")
_DIACRITICS_RE = re.compile(r"[ً-ٰٟ]")
_VOCAB_HW_RE = re.compile(r"^- \*\*(.+?)\*\*")
_GRAM_ITEM_RE = re.compile(r"^- `([^`]+)`")
_FORMS_LABEL_RE = re.compile(r"^- _(Forms?|Form)_:")
_META_LABEL_LINE_RE = re.compile(r"^- _")

# Suffixes to try stripping (longest first) when exact lookup fails.
_LOOKUP_SUFFIXES = [
    "هایشان", "هایتان", "هایمان", "هایی", "ترین", "مان", "تان", "شان",
    "های", "ند", "یم", "ان", "هاست", "ها", "یی", "ی", "ش", "ت", "م", "ه",
]


def _build_vocab_map(md_text: str) -> dict[str, str]:
    """Return {persian_form: anchor_id} for all vocab headwords, their
    backtick-quoted Forms entries, and grammar list items starting with
    a backtick-quoted Persian word."""
    word_map: dict[str, str] = {}
    current_anchor: str | None = None
    in_forms = False

    for raw_line in md_text.split("\n"):
        stripped = raw_line.lstrip()
        indent = len(raw_line) - len(stripped)

        if indent == 0:
            in_forms = False
            m = _VOCAB_HW_RE.match(stripped)
            if m:
                hw = m.group(1).strip()
                if _PERSIAN_CHAR_RE.search(hw):
                    current_anchor = f"vocab-{hw}"
                    word_map[hw] = current_anchor
                    # Also store diacritic-stripped form so source-text words
                    # with publisher diacritics (e.g. خُرّمساران) resolve to
                    # headwords that omit them (e.g. خرّمساران).
                    clean_hw = _DIACRITICS_RE.sub("", hw)
                    if clean_hw != hw and clean_hw not in word_map:
                        word_map[clean_hw] = current_anchor
                else:
                    current_anchor = None
            else:
                gm = _GRAM_ITEM_RE.match(stripped)
                if gm:
                    word = gm.group(1).strip()
                    if _PERSIAN_CHAR_RE.search(word) and " " not in word and word not in word_map:
                        word_map[word] = f"gram-{word}"
                current_anchor = None
        elif indent >= 2 and current_anchor:
            if _FORMS_LABEL_RE.match(stripped):
                in_forms = True
            elif _META_LABEL_LINE_RE.match(stripped):
                in_forms = False
            if in_forms:
                for tok in re.findall(r"`([^`]+)`", raw_line):
                    tok = tok.strip()
                    if _PERSIAN_CHAR_RE.search(tok) and " " not in tok and tok not in word_map:
                        word_map[tok] = current_anchor

    return word_map


def _lookup_word(word: str, word_map: dict[str, str]) -> str | None:
    """Return anchor id for `word`, trying diacritic-stripping and suffix
    stripping as fallbacks."""
    if word in word_map:
        return word_map[word]
    clean = _DIACRITICS_RE.sub("", word)
    if clean != word and clean in word_map:
        return word_map[clean]
    for suffix in _LOOKUP_SUFFIXES:
        if clean.endswith(suffix) and len(clean) - len(suffix) >= 2:
            stem = clean[: -len(suffix)]
            if stem in word_map:
                return word_map[stem]
    return None


def _link_source_text(
    text: str,
    word_map: dict[str, str],
    unlinked: list[str] | None = None,
) -> str:
    """Convert raw source-text content (from inside backticks, before any
    _inline() processing) to HTML with Persian words linked to vocab/grammar
    entries and {e} markers converted to ezafe spans.

    If `unlinked` is provided, any token that could not be resolved is appended
    to it so the caller can emit warnings."""
    result: list[str] = []
    parts = re.split(r"\{e\}", text)
    for i, part in enumerate(parts):
        if i > 0:
            result.append('<span class="ezafe">ِ</span>')
        last = 0
        for m in _PERSIAN_TOKEN_RE.finditer(part):
            before = part[last : m.start()]
            if before:
                result.append(html_lib.escape(before))
            word = m.group(0)
            anchor = _lookup_word(word, word_map)
            if anchor:
                result.append(
                    f'<a href="#{anchor}" class="src-link">{html_lib.escape(word)}</a>'
                )
            else:
                result.append(html_lib.escape(word))
                if unlinked is not None:
                    unlinked.append(word)
            last = m.end()
        tail = part[last:]
        if tail:
            result.append(html_lib.escape(tail))
    return "".join(result)


# ---------- interlinear gloss ----------

_GL_ABBR_RE = re.compile(r'([A-Z]{2,}[0-9]?|[0-9][A-Z]{2,})')


def _render_gloss_line(text: str) -> str:
    """Render a [gloss] paragraph into an interlinear HTML block.

    Input: space-separated `persian|gloss` tokens. `|` separates the source
    word from its Leipzig-style gloss. Uppercase abbreviations in the gloss
    part (EZ, ACC, PST, 3PL, …) are wrapped in <span class="gl"> for
    small-caps rendering. Tokens without `|` are treated as bare labels.
    """
    units: list[str] = []
    for token in text.split():
        if "|" in token:
            src, tag = token.split("|", 1)
            src_html = html_lib.escape(src)
            tag_escaped = html_lib.escape(tag)
            tag_html = _GL_ABBR_RE.sub(
                r'<span class="gl">\1</span>', tag_escaped
            )
            units.append(
                f'<div class="gloss-unit">'
                f'<span class="gloss-src">{src_html}</span>'
                f'<span class="gloss-tag">{tag_html}</span>'
                f"</div>"
            )
        else:
            escaped = html_lib.escape(token)
            units.append(
                f'<div class="gloss-unit">'
                f'<span class="gloss-src">{escaped}</span>'
                f'<span class="gloss-tag"></span>'
                f"</div>"
            )
    words_html = "\n".join(units)
    return f'<div class="gloss"><div class="gloss-words">\n{words_html}\n</div></div>'


# ---------- Markdown table renderer ----------


def _render_table(rows: list[str]) -> str:
    """Render pipe-delimited Markdown table rows as an HTML table.

    Data cells whose content matches `A // B // C` are rendered as three
    stacked spans (.cell-fa / .cell-tr / .cell-en) for Persian, romanization,
    and English respectively.
    """
    if len(rows) < 2:
        return ""

    def split_row(raw: str) -> list[str]:
        return [c.strip() for c in raw.strip().strip("|").split("|")]

    def render_cell(content: str, tag: str = "td") -> str:
        # Extract a leading <span id="..."> anchor so it survives html.escape().
        anchor_prefix = ""
        am = _CELL_ANCHOR_RE.match(content)
        if am:
            anchor_prefix = f'<span id="{am.group(1)}">{_inline(am.group(2))}</span>'
            content = am.group(3).lstrip()
        if tag == "td" and "//" in content:
            parts = [p.strip() for p in content.split("//", 2)]
            if len(parts) == 3:
                fa, tr, en = parts
                inner = (
                    f'<span class="cell-fa">{_inline(fa)}</span>'
                    f'<span class="cell-tr">{_inline(tr)}</span>'
                    f'<span class="cell-en">{_inline(en)}</span>'
                )
                return f'<{tag} class="cell-3">{anchor_prefix}{inner}</{tag}>'
        return f"<{tag}>{anchor_prefix}{_inline(content)}</{tag}>"

    header_cells = split_row(rows[0])
    sep_stripped = rows[1].replace("|", "").replace("-", "").replace(":", "").replace(" ", "").strip()
    if sep_stripped == "":
        data_rows = rows[2:]
    else:
        data_rows = rows[1:]
        header_cells = None  # type: ignore[assignment]

    out = ['<table class="conj-table">']
    if header_cells is not None:
        out.append("<thead><tr>")
        for cell in header_cells:
            out.append(render_cell(cell, "th"))
        out.append("</tr></thead>")
    ncols = len(header_cells) if header_cells is not None else (
        len(split_row(data_rows[0])) if data_rows else 1
    )
    out.append("<tbody>")
    for raw_row in data_rows:
        cells = split_row(raw_row)
        out.append("<tr>")
        # If only the first cell has content, span it across all columns.
        if cells[0] and not any(cells[1:]):
            out.append(f'<td colspan="{ncols}" class="span-cell">{_inline(cells[0])}</td>')
        else:
            for cell in cells:
                out.append(render_cell(cell))
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


# ---------- table of contents ----------


def _build_toc(md: str) -> str:
    """Generate a <nav class="toc"> from H2/H3 headings in the markdown."""
    headings: list[tuple[int, str, str]] = []
    for line in md.split("\n"):
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) in (2, 3):
            raw = m.group(2)
            headings.append((len(m.group(1)), raw, _slug(raw)))
    if not headings:
        return ""

    items: list[str] = []
    i = 0
    while i < len(headings):
        level, raw, slug = headings[i]
        label = _inline(raw)
        if level == 2:
            children: list[str] = []
            j = i + 1
            while j < len(headings) and headings[j][0] == 3:
                _, craw, cslug = headings[j]
                children.append(f'<li><a href="#{cslug}">{_inline(craw)}</a></li>')
                j += 1
            if children:
                items.append(
                    f'<li><a href="#{slug}">{label}</a>'
                    f'<ul>{"".join(children)}</ul></li>'
                )
                i = j
            else:
                items.append(f'<li><a href="#{slug}">{label}</a></li>')
                i += 1
        else:
            items.append(f'<li><a href="#{slug}">{_inline(raw)}</a></li>')
            i += 1

    return (
        '<nav class="toc"><p class="toc-title">Contents</p><ul>'
        + "".join(items)
        + "</ul></nav>"
    )


# ---------- post-processing: vocab entries ----------

LINE_REF_RE = re.compile(
    r"^(<a\b[^>]+>[^<]+</a>:|Lines?\s+[\d–—\-]+:)\s*(.*)$",
    re.DOTALL,
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


# ---------- editorial-ezafe toggle ----------

# Switch injected immediately before any block (paragraph or grammar
# example) that contains a `<span class="ezafe">…</span>`. Built as a
# label-wrapped checkbox so it's keyboard-accessible; the visible
# track/thumb is styled in CSS via `:checked` sibling selectors. The
# inline `<script>` in DOCUMENT delegates `change` events on the hidden
# checkboxes — flipping a `hide-ezafe` class on `<body>` (which CSS
# uses to hide every `.ezafe`) and mirroring the new state to every
# other toggle on the page so any switch reflects/controls the same
# global setting. Defaults to checked = ezafe visible.
EZAFE_TOGGLE_HTML = (
    '<label class="ezafe-toggle">'
    '<span class="ezafe-toggle-text">Editorial ezafe</span>'
    '<input type="checkbox" class="ezafe-toggle-input" checked'
    ' aria-label="Show editorial ezafe markers">'
    '<span class="ezafe-toggle-track" aria-hidden="true"></span>'
    "</label>"
)

TRANSLATION_TOGGLE_HTML = (
    '<label class="translation-toggle">'
    '<span class="translation-toggle-text">Translation</span>'
    '<input type="checkbox" class="translation-toggle-input"'
    ' aria-label="Show translations">'
    '<span class="translation-toggle-track" aria-hidden="true"></span>'
    "</label>"
)

GLOSS_TOGGLE_HTML = (
    '<label class="gloss-toggle">'
    '<span class="gloss-toggle-text">Gloss</span>'
    '<input type="checkbox" class="gloss-toggle-input"'
    ' aria-label="Show interlinear gloss">'
    '<span class="gloss-toggle-track" aria-hidden="true"></span>'
    "</label>"
)

TOGGLE_BAR_HTML = (
    f'<div class="toggle-bar">'
    f'{EZAFE_TOGGLE_HTML}{TRANSLATION_TOGGLE_HTML}{GLOSS_TOGGLE_HTML}'
    f'</div>'
)
EZAFE_TOGGLE_BAR_HTML = f'<div class="toggle-bar">{EZAFE_TOGGLE_HTML}</div>'


def _has_ezafe(html: str) -> bool:
    return 'class="ezafe"' in html


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
    body = "\n".join(out)
    if _has_ezafe(body):
        body = EZAFE_TOGGLE_BAR_HTML + "\n" + body
    return body


# ---------- block-level parser ----------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
HR_SET = {"---", "***", "___"}
LIST_RE = re.compile(r"^(\s*)-\s+(.+)$")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|")


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


META_LABEL_RE = re.compile(r"^<em>([^<]+?)</em>")
KNOWN_META_LABELS = {
    "etym": "vocab-etym",
    "etymology": "vocab-etym",
    "form": "vocab-forms",
    "forms": "vocab-forms",
    "family": "vocab-family",
    "kin": "vocab-family",
}


def _detect_meta_class(content: str) -> str:
    """Inspect a vocab-meta sub-bullet and return its CSS class."""
    m = META_LABEL_RE.match(content)
    if m:
        label = m.group(1).strip().lower().rstrip(":").rstrip()
        if label in KNOWN_META_LABELS:
            return KNOWN_META_LABELS[label]
    return "vocab-meta-other"


def _wrap_meta_label(content: str) -> str:
    """Promote the leading <em>Label</em> chip to <span class="meta-label">."""
    return META_LABEL_RE.sub(
        lambda m: f'<span class="meta-label">{m.group(1).rstrip(":").strip()}</span>',
        content,
        count=1,
    )


def _emit_tree(
    nodes: list[tuple[str, list]], depth: int = 0, mode: str = "plain"
) -> str:
    """Emit properly-nested HTML from a tree of nodes.

    `mode` is one of:
      - "plain": ordinary list (default)
      - "vocab": top-level vocab list; items get .vocab-entry, children render as "meta"
      - "meta":  metadata sub-list under a vocab entry; items get
                 .vocab-etym / .vocab-forms / .vocab-meta-other based on label
    """
    sp = "  " * depth
    if mode == "vocab":
        ul_attr = ' class="vocab"'
    elif mode == "meta":
        ul_attr = ' class="vocab-meta"'
    else:
        ul_attr = ""

    out: list[str] = [f"{sp}<ul{ul_attr}>"]
    for content, children in nodes:
        if mode == "vocab":
            _hw_m = re.search(r"<strong>([^<]+)</strong>", content)
            if _hw_m:
                _hw = _hw_m.group(1).strip()
                _hw_id = f' id="vocab-{_hw}"' if _hw else ""
                li_open = f'<li class="vocab-entry"{_hw_id}>'
            else:
                # Code-starting alias entry within a vocab list (e.g. `سرورا`)
                _code_m = re.match(r"<code>([؀-ۿ‌][^<]*)</code>", content)
                if _code_m:
                    li_open = f'<li id="gram-{_code_m.group(1).strip()}">'
                else:
                    li_open = "<li>"
            li_content = _wrap_vocab_entry(content)
            child_mode = "meta"
        elif mode == "meta":
            cls = _detect_meta_class(content)
            li_open = f'<li class="{cls}">'
            li_content = _wrap_meta_label(content)
            child_mode = "plain"
        else:
            _code_m = re.match(r"<code>([؀-ۿ‌][^<]*)</code>", content)
            if _code_m:
                _gram_word = _code_m.group(1).strip()
                li_open = f'<li id="gram-{_gram_word}">'
            else:
                li_open = "<li>"
            li_content = content
            child_mode = "plain"

        if children:
            out.append(f"{sp}  {li_open}{li_content}")
            out.append(_emit_tree(children, depth + 2, mode=child_mode))
            out.append(f"{sp}  </li>")
        else:
            out.append(f"{sp}  {li_open}{li_content}</li>")
    out.append(f"{sp}</ul>")
    return "\n".join(out)


def _emit_list(items: list[tuple[int, str]]) -> str:
    """Render a flat list of (indent_level, html) into nested <ul>/<li>.

    A top-level list whose items all start with <strong> is tagged class="vocab"
    (vocab list); each item gets class="vocab-entry" and its sub-list (if any)
    becomes a class="vocab-meta" block whose items are tagged .vocab-etym /
    .vocab-forms / .vocab-meta-other based on their leading *italic label*.

    A list is classified as vocab if at least one top-level item has a bold
    Persian headword — this tolerates mixed lists where code-starting alias
    entries (e.g. a backtick-quoted word) appear alongside bold vocab headwords.
    """
    top_items_content = [c for indent, c in items if indent == 0]
    top_is_vocab = bool(top_items_content) and any(
        (m := re.search(r"<strong>([^<]+)</strong>", c))
        and _PERSIAN_CHAR_RE.search(m.group(1))
        for c in top_items_content
    )
    tree, _ = _build_tree(items, 0, 0)
    return _emit_tree(tree, depth=0, mode="vocab" if top_is_vocab else "plain")


GRAMMAR_FENCE = ">>>"


def _render_body(
    md: str,
    word_map: dict[str, str] | None = None,
    unlinked: list[str] | None = None,
) -> str:
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    in_grammar = False

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Grammar-note fence: >>> opens/closes a styled block.
        # The line immediately after the opening >>> is the block title (h4).
        if stripped == GRAMMAR_FENCE:
            if not in_grammar:
                in_grammar = True
                i += 1
                while i < n and not lines[i].strip():
                    i += 1
                if i < n:
                    title_raw = lines[i].strip()
                    title_html = _inline(title_raw)
                    slug = _slug(title_raw)
                    out.append(
                        f'<div class="grammar-note-block">'
                        f'<h4 class="grammar-note" id="{slug}">{title_html}</h4>'
                    )
                    i += 1
            else:
                in_grammar = False
                out.append("</div>")
                i += 1
            continue

        # Horizontal rule
        if stripped in HR_SET:
            out.append("<hr>")
            i += 1
            continue

        # Heading
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            content = _inline(m.group(2))
            slug = _slug(m.group(2))
            out.append(f'<h{level} id="{slug}">{content}</h{level}>')
            i += 1
            continue

        # Blockquote — consume consecutive > lines as a single example
        if BLOCKQUOTE_RE.match(line):
            bq_lines: list[str] = []
            while i < n:
                if lines[i].strip() == GRAMMAR_FENCE:
                    break
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

        # Source text, gloss, and translation directives — each line is standalone
        _src_m = re.match(r"^`([^`]+)`$", stripped) if word_map is not None else None
        _trans_m = re.match(r"^\[(en|lit)\]\s+(.+)$", stripped, re.DOTALL)
        _gloss_m = re.match(r"^\[gloss\]\s+(.+)$", stripped, re.DOTALL)
        if _src_m:
            _inner = _link_source_text(_src_m.group(1), word_map, unlinked)
            out.append(TOGGLE_BAR_HTML)
            out.append(f'<p class="source-text"><code>{_inner}</code></p>')
            i += 1
            continue
        if _gloss_m:
            out.append(_render_gloss_line(_gloss_m.group(1)))
            i += 1
            continue
        if _trans_m:
            lang = _trans_m.group(1)
            cls = "translation-en" if lang == "en" else "translation-lit"
            out.append(f'<div class="translation {cls}">{_inline(_trans_m.group(2))}</div>')
            i += 1
            continue

        # Table — consume all consecutive pipe-prefixed lines
        if _TABLE_ROW_RE.match(stripped):
            table_rows: list[str] = []
            while i < n and _TABLE_ROW_RE.match(lines[i].strip()):
                table_rows.append(lines[i])
                i += 1
            out.append(_render_table(table_rows))
            continue

        # [TOC] directive — generate table of contents
        if stripped == "[TOC]":
            out.append(_build_toc(md))
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
                or _TABLE_ROW_RE.match(ps)
                or ps == "[TOC]"
                or re.match(r"^\[(en|lit|gloss)\]\s", ps)
                or (word_map is not None and re.match(r"^`[^`]+`$", ps))
            ):
                break
            para.append(ps)
            i += 1
        if para:
            raw = " ".join(para)
            rendered = f"<p>{_inline(raw)}</p>"
            if _has_ezafe(rendered):
                out.append(EZAFE_TOGGLE_BAR_HTML)
            out.append(rendered)

    if in_grammar:
        out.append("</div>")

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
<body{body_class}>
<main>
{nav}
{body}
{nav}
</main>
<script>
(function () {{
  document.addEventListener('change', function (e) {{
    var t = e.target;
    if (!t || !t.classList) return;
    if (t.classList.contains('ezafe-toggle-input')) {{
      var v = t.checked;
      document.body.classList.toggle('hide-ezafe', !v);
      var ins = document.querySelectorAll('.ezafe-toggle-input');
      for (var i = 0; i < ins.length; i++) ins[i].checked = v;
    }}
    if (t.classList.contains('translation-toggle-input')) {{
      var v = t.checked;
      document.body.classList.toggle('show-translations', v);
      var ins = document.querySelectorAll('.translation-toggle-input');
      for (var i = 0; i < ins.length; i++) ins[i].checked = v;
    }}
    if (t.classList.contains('gloss-toggle-input')) {{
      var v = t.checked;
      document.body.classList.toggle('show-gloss', v);
      var ins = document.querySelectorAll('.gloss-toggle-input');
      for (var i = 0; i < ins.length; i++) ins[i].checked = v;
    }}
  }});
}})();
</script>
</body>
</html>
"""


def render(md_text: str, css_href: str = "../styles.css", source_name: str = "") -> str:
    word_map = _build_vocab_map(md_text)
    unlinked: list[str] = []
    body = _render_body(md_text, word_map=word_map, unlinked=unlinked)
    if unlinked:
        counts: dict[str, int] = {}
        for w in unlinked:
            counts[w] = counts.get(w, 0) + 1
        label = f"{source_name}: " if source_name else ""
        for word, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {label}unlinked: {word} (×{n})", file=sys.stderr)
    # Prefer the first H1 as the document title
    m = re.search(r"^#\s+(.+)$", md_text, flags=re.MULTILINE)
    title = _inline(m.group(1)) if m else "Study Guide"
    # Strip any HTML from the title for the <title> element
    plain_title = re.sub(r"<[^>]+>", "", title)
    # Derive a page-specific body class from the source filename stem
    page_stem = Path(source_name).stem if source_name else ""
    body_class = f' class="page-{page_stem}"' if page_stem else ""
    index_href = str(Path(css_href).parent / ".." / "index.html")
    nav = f'<nav class="up-nav"><a href="{index_href}">↑ Study Guides</a></nav>'
    return DOCUMENT.format(title=plain_title, css=css_href, body=body, body_class=body_class, nav=nav)


# ---------- CLI ----------

def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <input.md> <output.html>", file=sys.stderr)
        return 2
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    md_text = in_path.read_text(encoding="utf-8")
    html = render(md_text, source_name=str(in_path))
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({len(html):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

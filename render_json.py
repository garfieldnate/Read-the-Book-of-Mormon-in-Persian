#!/usr/bin/env python3
"""Render a chapter study guide from structured JSON data to semantic HTML.

Source data comes from two JSON files per chapter:
  chN.source.json — pre-tokenized scripture text, interlinear gloss, English translation
  chN.study.json  — intro prose, vocab entries (headwords, variants), grammar notes

Output is the same HTML structure and CSS classes as render.py, so the same
stylesheet applies without modification.

Usage:
    python3 render_json.py <source.json> <study.json> <output.html>
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
from pathlib import Path

from render import (
    DOCUMENT,
    TOGGLE_BAR_HTML,
    EZAFE_TOGGLE_BAR_HTML,
    _inline,
    _build_example,
    _render_gloss_line,
    _slug,
    _has_ezafe,
    _PERSIAN_CHAR_RE,
    _DIACRITICS_RE,
    _LOOKUP_SUFFIXES,
)

# Maps arabic_form field values → anchor on arabic.html.
# Verbal noun Forms II–X and all participles have per-row span anchors.
_ARABIC_FORM_ANCHORS: dict[str, str] = {
    # Form I verbal noun → section heading (many patterns, no single row)
    "Form I verbal noun":     "verbal-nouns-form-i",
    # Forms II–X verbal nouns → per-form row anchors
    "Form II verbal noun":    "form-II",
    "Form III verbal noun":   "form-III",
    "Form IV verbal noun":    "form-IV",
    "Form V verbal noun":     "form-V",
    "Form VI verbal noun":    "form-VI",
    "Form VII verbal noun":   "form-VII",
    "Form VIII verbal noun":  "form-VIII",
    "Form IX verbal noun":    "form-IX",
    "Form X verbal noun":     "form-X",
    # Active participles → per-form row anchors
    "Form I active participle":   "form-I-act",
    "Form II active participle":  "form-II-act",
    "Form III active participle": "form-III-act",
    "Form IV active participle":  "form-IV-act",
    "Form X active participle":   "form-X-act",
    # Passive participles → per-form row anchors
    "Form I passive participle":  "form-I-pass",
    "Form II passive participle": "form-II-pass",
    "Form IV passive participle": "form-IV-pass",
    # Nominal patterns → per-row anchors in Other nominal patterns
    "elative (Form IV)":          "nom-ʾafʿal",
    "nominal pattern":            "other-nominal-patterns",
    "nisba relational adjective (-iyyun)": "nom-nisba",
}


# ---------- prose rendering (multi-paragraph markdown, no source-text blocks) ----------

def _render_prose(text: str, word_map: dict[str, str] | None = None) -> str:
    """Render a plain-markdown prose string to <p> blocks.

    Splits on blank lines; renders each paragraph via _inline().  Safe for
    intro/body/closing fields that will never contain source-text lines or
    grammar fences.
    """
    paras = re.split(r"\n{2,}", text.strip())
    out: list[str] = []
    for para in paras:
        if not para.strip():
            continue
        rendered = f"<p>{_inline(para.replace(chr(10), ' '), word_map)}</p>"
        if _has_ezafe(rendered):
            out.append(EZAFE_TOGGLE_BAR_HTML)
        out.append(rendered)
    return "\n".join(out)


# Imperfective prefix tokens — linked contextually to the following verb, not as own entries.
_MI_PREFIX: frozenset[str] = frozenset({"می", "نمی"})


# ---------- vocab map construction ----------

def _build_vocab_map_json(study: dict) -> dict[str, str]:
    """Return {persian_form: anchor_id} from the structured study JSON.

    Registers:
      - each headword's `persian` and `id` fields
      - every `fa` token in each headword's `forms` array
      - each variant entry's `persian` under a gram- anchor
    Also stores diacritic-stripped duplicates as fallback lookups.
    """
    word_map: dict[str, str] = {}

    def _register(form: str, anchor: str) -> None:
        if form in word_map:
            return
        word_map[form] = anchor
        clean = _DIACRITICS_RE.sub("", form)
        if clean != form and clean not in word_map:
            word_map[clean] = anchor

    # Pass 1: register headword and variant anchors so they can't be shadowed
    # by compound-form splits in pass 2.
    for section in study.get("sections", []):
        for entry in section.get("entries", []):
            etype = entry.get("type")
            if etype == "headword":
                persian = entry["persian"]
                entry_id = entry.get("id") or persian.replace(" ", "_")
                anchor = f"vocab-{entry_id}"
                _register(persian, anchor)
                if entry_id != persian:
                    _register(entry_id, anchor)
            elif etype == "variant":
                _register(entry["persian"], f"gram-{entry['persian']}")

    # Pass 2: register form tokens (including split components of compound forms).
    # Headwords from pass 1 already hold their slots, so first-wins is safe.
    for section in study.get("sections", []):
        for entry in section.get("entries", []):
            if entry.get("type") == "headword":
                entry_id = entry.get("id") or entry["persian"].replace(" ", "_")
                anchor = f"vocab-{entry_id}"
                for form in entry.get("forms") or []:
                    fa = form.get("fa")
                    if fa and _PERSIAN_CHAR_RE.search(fa):
                        _register(fa, anchor)
                        if " " in fa:
                            for tok in fa.split():
                                if tok and tok not in _MI_PREFIX and _PERSIAN_CHAR_RE.search(tok):
                                    _register(tok, anchor)

    return word_map


def _build_pos_map_json(study: dict) -> dict[str, str]:
    """Return {persian_form: pos} from the structured study JSON.

    Mirrors `_build_vocab_map_json` but stores each headword's part of speech
    (`noun`, `adj`, `propn`, `adp`, …) instead of its anchor, so source tokens
    can be classified for the editorial-ezafe lint. Registers each headword's
    `persian` and `id`, plus every full `fa` token in its `forms` array.

    Compound forms are deliberately **not** split into components — a part's POS
    can differ from the whole lexeme's (e.g. the noun `نصیحت` inside the compound
    verb `نصیحت کردن`), and a wrong POS would mislead the lint. Diacritic-stripped
    duplicates are registered as fallbacks, matching `_resolve_anchor`.
    """
    pos_map: dict[str, str] = {}

    def _register(form: str, pos: str) -> None:
        if not form or not pos or form in pos_map:
            return
        pos_map[form] = pos
        clean = _DIACRITICS_RE.sub("", form)
        if clean != form and clean not in pos_map:
            pos_map[clean] = pos

    for section in study.get("sections", []):
        for entry in section.get("entries", []):
            if entry.get("type") != "headword":
                continue
            pos = entry.get("pos")
            if not pos:
                continue
            _register(entry["persian"], pos)
            if entry.get("id"):
                _register(entry["id"], pos)
            for form in entry.get("forms") or []:
                fa = form.get("fa")
                if fa and _PERSIAN_CHAR_RE.search(fa):
                    _register(fa, pos)

    return pos_map


# ---------- source token rendering ----------

def _resolve_anchor(lookup_key: str, word_map: dict[str, str]) -> str | None:
    """Resolve a Persian token to a vocab-map anchor, with fallback suffix stripping."""
    anchor = word_map.get(lookup_key)
    if anchor is None:
        clean = _DIACRITICS_RE.sub("", lookup_key)
        if clean != lookup_key:
            anchor = word_map.get(clean)
        if anchor is None:
            for suffix in _LOOKUP_SUFFIXES:
                if clean.endswith(suffix) and len(clean) - len(suffix) >= 2:
                    stem = clean[: -len(suffix)]
                    if stem in word_map:
                        return word_map[stem]
    return anchor


def _render_tokens(
    tokens: list[dict],
    word_map: dict[str, str],
    unlinked: list[tuple[str, str]] | None = None,
    location: str = "",
) -> str:
    """Render a source-JSON tokens array to linked HTML.

    Token types:
      {"fa": "...", "lemma"?: "...", "e"?: true}  — Persian word or compound
      {"p": "..."}                                 — punctuation (no link, no leading space)

    می/نمی prefix tokens are combined with the immediately following verb token
    into a single <a> link so they read as one unit rather than two separate links.
    """
    result: list[str] = []
    prev_was_word = False
    tok_list = list(tokens)
    i = 0

    while i < len(tok_list):
        tok = tok_list[i]
        if "fa" in tok:
            fa = tok["fa"]
            lookup_key = tok.get("lemma") or fa

            if prev_was_word:
                result.append(" ")

            # می/نمی prefix: combine with the next verb token as one linked unit.
            if fa in _MI_PREFIX and i + 1 < len(tok_list) and "fa" in tok_list[i + 1]:
                next_tok = tok_list[i + 1]
                next_fa = next_tok["fa"]
                next_lookup = next_tok.get("lemma") or next_fa
                next_anchor = _resolve_anchor(next_lookup, word_map)
                if next_anchor is None and next_lookup != next_fa:
                    next_anchor = _resolve_anchor(next_fa, word_map)
                if next_anchor:
                    combined = f'{html_lib.escape(fa)} {html_lib.escape(next_fa)}'
                    result.append(f'<a href="#{next_anchor}" class="src-link">{combined}</a>')
                    if next_tok.get("e"):
                        result.append('<span class="ezafe">ِ</span>')
                    prev_was_word = True
                    i += 2
                    continue
                # Next token has no anchor — fall through and render می unlinked below

            # Normal token: look up in vocab map with suffix-stripping fallback
            anchor = _resolve_anchor(lookup_key, word_map)
            if anchor is None and lookup_key != fa:
                anchor = _resolve_anchor(fa, word_map)

            fa_html = html_lib.escape(fa)
            if anchor:
                result.append(f'<a href="#{anchor}" class="src-link">{fa_html}</a>')
            else:
                result.append(fa_html)
                if unlinked is not None:
                    unlinked.append((fa, location))

            if tok.get("e"):
                result.append('<span class="ezafe">ِ</span>')

            prev_was_word = True

        elif "p" in tok:
            result.append(html_lib.escape(tok["p"]))
            # Space after sentence/clause-ending punctuation; not after em-dash
            # or other separators that intentionally run words together.
            prev_was_word = tok["p"] in (".", "،", "؛", ":", "!", "؟", "?")

        i += 1

    return "".join(result)


# ---------- gloss rendering ----------

def _render_gloss_from_tokens(tokens: list[dict]) -> str:
    """Render interlinear gloss from gloss sub-objects embedded in token objects."""
    pairs = [t["gloss"] for t in tokens if "fa" in t and "gloss" in t]
    if not pairs:
        return ""
    flat = " ".join(f"{g['src']}|{g['gloss']}" for g in pairs)
    return _render_gloss_line(flat)


# ---------- section heading helpers ----------

_BOOK_SUMMARY_TYPES = frozenset({
    "book-summary-title", "book-summary-subtitle", "book-summary-sentence"
})


def _section_type(sec: dict) -> str:
    return sec.get("type") or sec.get("section_type", "")


def _section_heading(sec: dict) -> tuple[int, str, str]:
    """Return (html_level, heading_text, anchor_id) for a section."""
    t = _section_type(sec)
    n = sec.get("number")
    if t == "chapter-summary":
        return 3, "Chapter summary", "chapter-summary"
    if t == "verse":
        return 3, f"Verse {n}", f"verse-{n}"
    if t == "book-summary-title":
        return 4, "Title", "title"
    if t == "book-summary-subtitle":
        return 4, "Subtitle", "subtitle"
    if t == "book-summary-sentence":
        return 4, f"Sentence {n}", f"sentence-{n}"
    return 3, t.replace("-", " ").title(), _slug(t)


# ---------- forms rendering ----------

def _render_forms_html(forms: list[dict], anchor: str, word_map: dict[str, str]) -> str:
    """Build the inner HTML for a _Forms_ sub-bullet from a structured forms array."""
    parts: list[str] = []
    for form in forms:
        if "note" in form:
            parts.append(_inline(form["note"], word_map))
        else:
            fa   = form.get("fa", "")
            desc = form.get("desc", "")
            # Migration-style: desc already contains the fa in backticks — just render desc
            # so the Persian form is not prepended twice.
            fa_in_desc = fa and (
                f"`{fa}`" in desc or
                any(f"`{t}`" in desc for t in fa.split() if t)
            )
            if fa_in_desc:
                parts.append(_inline(desc, word_map))
            else:
                translit = form.get("translit")
                fa_html  = html_lib.escape(fa)
                linked   = f'<bdi><a href="#{anchor}" class="src-link"><code>{fa_html}</code></a></bdi>'
                seg      = linked
                if translit:
                    seg += f' <em class="translit">{html_lib.escape(translit)}</em>'
                if desc:
                    seg += " " + _inline(desc, word_map)
                parts.append(seg)
    return "; ".join(parts)


# ---------- entry rendering ----------

def _render_root_tag(root: str) -> str:
    return f'<span class="root-tag">{html_lib.escape(root)}</span>'


def _render_plural_line(plural: dict | None, word_map: dict[str, str]) -> str:
    """Render the pl-forms line from a `plural` entry field.

    Suffix forms are listed first, broken forms second, separated by ·.
    Returns "" when plural is absent or has no forms.
    """
    if not plural:
        return ""
    suffixes = plural.get("suffixes") or []
    broken   = plural.get("broken")   or []

    all_forms: list[str] = []

    for form in suffixes:
        persian  = html_lib.escape(form.get("persian", ""))
        translit = html_lib.escape(form.get("translit", ""))
        note     = form.get("note", "")
        inner = f'<span class="persian">{persian}</span>'
        if translit:
            inner += f' <em class="translit">{translit}</em>'
        if note:
            inner += f' <span class="pl-form-note">({html_lib.escape(note)})</span>'
        all_forms.append(f'<span class="pl-form">{inner}</span>')

    for form in broken:
        persian  = html_lib.escape(form.get("persian", ""))
        translit = html_lib.escape(form.get("translit", ""))
        note     = form.get("note", "")
        inner = f'<span class="persian">{persian}</span>'
        if translit:
            inner += f' <em class="translit">{translit}</em>'
        inner += ' <span class="pl-broken-label">broken</span>'
        if note:
            inner += f' <span class="pl-form-note">({html_lib.escape(note)})</span>'
        all_forms.append(f'<span class="pl-form pl-broken">{inner}</span>')

    if not all_forms:
        return ""

    sep = '<span class="pl-sep">·</span>'
    forms_html = f" {sep} ".join(all_forms)
    return f'<div class="pl-forms"><span class="pl-label">pl.</span> {forms_html}</div>'


def _render_light_verb_line(entry: dict) -> str:
    """Render the compound-verb line for entries with a `light_verb` field.

    Each element: → [noun + verb]  translit  "meaning"
    Multiple elements separated by ·.
    """
    lvs = entry.get("light_verb")
    if not lvs:
        return ""
    persian_base  = html_lib.escape(entry.get("persian", ""))
    translit_base = entry.get("translit", "")
    # Strip any parenthetical pres-stem suffix from translit for the compound
    translit_base = re.sub(r"\s*\(pres\..*\)\s*$", "", translit_base).strip()

    compounds: list[str] = []
    for lv in lvs:
        verb_fa  = html_lib.escape(lv.get("verb", ""))
        verb_tr  = html_lib.escape(lv.get("translit", ""))
        meaning  = html_lib.escape(lv.get("meaning", ""))
        cpd_fa   = f'{persian_base} {verb_fa}'
        cpd_tr   = f'{html_lib.escape(translit_base)} {verb_tr}' if translit_base else verb_tr

        inner = (
            f'<span class="persian">{cpd_fa}</span>'
            f' <em class="translit">{cpd_tr}</em>'
        )
        if meaning:
            inner += f' <span class="lv-meaning">"{meaning}"</span>'
        compounds.append(f'<span class="lv-compound">{inner}</span>')

    sep = ' <span class="lv-sep">·</span> '
    return (
        f'<div class="lv-forms">'
        f'<span class="lv-arrow">→</span> '
        f'{sep.join(compounds)}'
        f'</div>'
    )


def _render_arabic_form_tag(arabic_form: str, arabic_href: str) -> str:
    anchor = _ARABIC_FORM_ANCHORS.get(arabic_form, "pattern-reference")
    label = html_lib.escape(arabic_form)
    return f'<a href="{arabic_href}#{anchor}" class="arabic-form-tag">{label}</a>'


def _render_headword_entry(entry: dict, word_map: dict[str, str], arabic_href: str = "") -> str:
    persian = entry["persian"]
    translit = entry.get("translit", "")
    meaning = entry.get("meaning", "")
    tags = entry.get("tags") or []
    pres_stem = entry.get("pres_stem")
    entry_id = entry.get("id") or persian.replace(" ", "_")
    anchor = f"vocab-{entry_id}"

    # Headword line:  Persian — translit [(pres. stem)] — meaning [tags]
    line: list[str] = [f'<strong class="persian">{html_lib.escape(persian)}</strong>']

    for tag in tags:
        if tag == "bound-morpheme":
            line.append(f' <span class="proper">[bound morpheme]</span>')

    line.append(" — ")

    tr_html = f'<em class="translit">{_inline(translit, {})}</em>'
    if pres_stem and pres_stem.get("translit"):
        ps_tr = html_lib.escape(pres_stem["translit"])
        ps_fa = pres_stem.get("fa")
        if ps_fa:
            pres_html = (
                f'<em class="translit">{html_lib.escape(ps_fa)}</em>'
                f' (<em class="translit">{ps_tr}</em>)'
            )
        else:
            pres_html = f'<em class="translit">{ps_tr}</em>'
        line.append(f"{tr_html} (pres. {pres_html})")
    else:
        line.append(tr_html)

    for tag in tags:
        if tag == "proper":
            line.append(' <span class="proper">[proper]</span>')

    line.append(f" — {_inline(meaning, word_map)}")

    headword_html = "".join(line)

    # Meta sub-bullets
    meta: list[str] = []

    warning = entry.get("warning")
    if warning:
        meta.append(
            f'<li class="vocab-meta-other">⚠️ {_inline(warning, word_map)}</li>'
        )

    etym = entry.get("etym")
    if etym:
        if isinstance(etym, dict):
            prose = etym.get("prose", "")
            arabic_form = etym.get("arabic_form", "")
            root = etym.get("root", "")
        else:
            prose = etym
            arabic_form = ""
            root = ""
        root_tag = " " + _render_root_tag(root) if root else ""
        form_tag = (
            " " + _render_arabic_form_tag(arabic_form, arabic_href)
            if arabic_form and arabic_href
            else ""
        )
        meta.append(
            f'<li class="vocab-etym">'
            f'<span class="meta-label">Etym</span>: {_inline(prose, word_map)}{root_tag}{form_tag}'
            f'</li>'
        )

    family = entry.get("family")
    if family:
        meta.append(
            f'<li class="vocab-family">'
            f'<span class="meta-label">Family</span>: {_inline(family, word_map)}'
            f'</li>'
        )

    forms = entry.get("forms")
    if forms:
        forms_html = _render_forms_html(forms, anchor, word_map)
        meta.append(
            f'<li class="vocab-forms">'
            f'<span class="meta-label">Forms</span>: {forms_html}'
            f'</li>'
        )

    plural_note = (entry.get("plural") or {}).get("note")
    if plural_note:
        meta.append(
            f'<li class="vocab-plural">'
            f'<span class="meta-label">Plural</span>: {_inline(plural_note, word_map)}'
            f'</li>'
        )

    lv_html = _render_light_verb_line(entry)
    plural_html = _render_plural_line(entry.get("plural"), word_map)
    li_inner = headword_html
    if lv_html:
        li_inner += "\n" + lv_html
    if plural_html:
        li_inner += "\n" + plural_html
    if meta:
        li_inner += '\n<ul class="vocab-meta">\n' + "\n".join(meta) + "\n</ul>"

    return f'<li class="vocab-entry" id="{anchor}">{li_inner}</li>'


def _render_variant_entry(entry: dict, word_map: dict[str, str]) -> str:
    persian = entry["persian"]
    translit = entry.get("translit", "")
    meaning = entry.get("meaning", "")
    inner = f'<bdi><code>{html_lib.escape(persian)}</code></bdi>'
    if translit:
        inner += f' (<em class="translit">{html_lib.escape(translit)}</em>)'
    inner += f' — {_inline(meaning, word_map)}'
    return f'<li id="gram-{html_lib.escape(persian)}">{inner}</li>'


def _render_grammar_note(entry: dict, word_map: dict[str, str]) -> str:
    title_raw = entry.get("title", "")
    title_html = _inline(title_raw, word_map)
    slug = _slug(title_raw)
    body = entry.get("body", "")
    examples = entry.get("examples") or []
    closing = entry.get("closing", "")

    parts: list[str] = [
        f'<div class="grammar-note-block">',
        f'<h4 class="grammar-note" id="{slug}">{title_html}</h4>',
    ]

    if body:
        parts.append(_render_prose(body, word_map))

    for ex in examples:
        ref = ex.get("ref", "")
        ref_anchor = ex.get("ref_anchor", "")
        persian = ex.get("persian", "")
        translit = ex.get("translit", "")
        en_text = ex.get("en", "")

        ref_link = (
            f'<a href="#{html_lib.escape(ref_anchor)}">{html_lib.escape(ref)}</a>'
            if ref_anchor else html_lib.escape(ref)
        )
        persian_esc = html_lib.escape(persian).replace("{e}", '<span class="ezafe">ِ</span>')
        fa_line = f'{ref_link}: <code>{persian_esc}</code>'
        tr_line = f'<em>{html_lib.escape(translit)}</em>'
        en_line = _inline(en_text, word_map)
        ex_lines = [fa_line, tr_line] + ([en_line] if en_line else [])
        parts.append(_build_example(ex_lines))

    if closing:
        parts.append(_render_prose(closing, word_map))

    parts.append("</div>")
    return "\n".join(parts)


def _render_entries(entries: list[dict], word_map: dict[str, str], arabic_href: str = "") -> str:
    """Render all entries for a section, flushing vocab <ul> around grammar notes."""
    if not entries:
        return ""

    parts: list[str] = []
    vocab_buf: list[str] = []

    def _flush() -> None:
        if vocab_buf:
            parts.append('<ul class="vocab">\n' + "\n".join(vocab_buf) + "\n</ul>")
            vocab_buf.clear()

    for entry in entries:
        etype = entry.get("type")
        if etype == "headword":
            vocab_buf.append(_render_headword_entry(entry, word_map, arabic_href))
        elif etype == "variant":
            vocab_buf.append(_render_variant_entry(entry, word_map))
        elif etype == "no-new-lemmas":
            _flush()
            parts.append(
                "<p><em>No new lemmas — every word in this section "
                "has already been introduced.</em></p>"
            )
        elif etype == "grammar-note":
            _flush()
            parts.append(_render_grammar_note(entry, word_map))

    _flush()
    return "\n".join(parts)


# ---------- table of contents ----------

def _build_chapter_toc(source: dict, study: dict) -> str:
    """Build a <nav class="toc"> for a JSON-rendered chapter.

    Top-level items: Intro (if present), Vocabulary and Grammar, Grammar, closing.
    Vocabulary children: one item per source section, with book-summary-*
    sections collapsed into a single "Book summary" entry.
    Grammar children: all grammar-note entries across all study sections, in order.
    """
    items: list[str] = []

    if study.get("intro", "").strip():
        items.append('<li><a href="#intro">Intro</a></li>')

    if study.get("reading_tip", "").strip():
        items.append('<li><a href="#reading-tips">Reading tips</a></li>')

    study_index: dict[tuple[str, int | None], dict] = {}
    for s in study.get("sections", []):
        key = (_section_type(s), s.get("number"))
        study_index[key] = s

    vocab_children: list[str] = []
    book_summary_added = False
    for sec in source.get("sections", []):
        t = _section_type(sec)
        if t in _BOOK_SUMMARY_TYPES:
            if not book_summary_added:
                book_summary_added = True
                vocab_children.append('<li><a href="#book-summary">Book summary</a></li>')
        else:
            _, heading_text, heading_id = _section_heading(sec)
            vocab_children.append(
                f'<li><a href="#{heading_id}">{html_lib.escape(heading_text)}</a></li>'
            )

    if vocab_children:
        children_html = "".join(vocab_children)
        items.append(
            f'<li><a href="#vocabulary-and-grammar">Vocabulary and Grammar</a>'
            f'<ul>{children_html}</ul></li>'
        )
    else:
        items.append('<li><a href="#vocabulary-and-grammar">Vocabulary and Grammar</a></li>')

    grammar_children: list[str] = []
    for sec in source.get("sections", []):
        t = _section_type(sec)
        study_sec = study_index.get((t, sec.get("number")))
        for entry in (study_sec or {}).get("entries", []):
            if entry.get("type") == "grammar-note":
                title = entry["title"]
                grammar_children.append(
                    f'<li><a href="#{_slug(title)}">{html_lib.escape(title)}</a></li>'
                )

    if grammar_children:
        children_html = "".join(grammar_children)
        items.append(
            f'<li><a href="#vocabulary-and-grammar">Grammar</a>'
            f'<ul>{children_html}</ul></li>'
        )


    return (
        '<nav class="toc"><p class="toc-title">Contents</p><ul>'
        + "".join(items)
        + "</ul></nav>"
    )


# ---------- section rendering ----------

def _render_section(
    source_sec: dict,
    study_sec: dict | None,
    word_map: dict[str, str],
    unlinked: list[tuple[str, str]] | None,
    arabic_href: str = "",
) -> str:
    level, heading_text, heading_id = _section_heading(source_sec)
    location = heading_text

    parts: list[str] = [
        f'<h{level} id="{heading_id}">{html_lib.escape(heading_text)}</h{level}>'
    ]

    tokens = source_sec.get("tokens")
    if tokens is not None:
        tokens_html = _render_tokens(tokens, word_map, unlinked, location)
        parts.append(TOGGLE_BAR_HTML)
        parts.append(f'<p class="source-text"><code>{tokens_html}</code></p>')

    if tokens and any("gloss" in t for t in tokens if "fa" in t):
        parts.append(_render_gloss_from_tokens(tokens))

    en = source_sec.get("en")
    if en:
        parts.append(f'<div class="translation translation-en">{_inline(en, word_map)}</div>')

    if study_sec is not None:
        entries_html = _render_entries(study_sec.get("entries") or [], word_map, arabic_href)
        if entries_html:
            parts.append(entries_html)

    return "\n".join(parts)


# ---------- editorial-ezafe lint ----------
#
# Persian very rarely juxtaposes a noun and a following noun or adjective with no
# ezafe linker between them (true noun-noun compounds are uncommon), so an
# unmarked noun→noun or noun→adjective adjacency is a strong signal that an
# editorial ezafe (`"e": true`) was missed when the chapter was generated.
# These checks are heuristic — eyeball each finding before acting on it.

# POS that can host an ezafe (the head of an ezafe phrase) …
_EZAFE_HEAD_POS = frozenset({"noun", "propn"})
# … and POS that can follow it as the modifier (possessor noun or adjective).
_EZAFE_MOD_POS = frozenset({"noun", "propn", "adj"})

# Leipzig labels that mark a token as a (finite or non-finite) verb form. A
# token glossed with any of these is functioning verbally here, whatever its
# citation POS — so it is neither an ezafe head nor an ezafe modifier. This also
# fixes noun/verb homographs that the POS map resolves to the noun (e.g. `هستی`
# "you are", glossed `be-PRS-2SG`).
_VERBAL_TAGS = frozenset({
    "PST", "PRS", "FUT", "SBJV", "PTCP", "COP", "IMPF", "NARR", "PASS", "INF",
})
# English gloss stems of the common light/compound-verb operators. A nominal
# directly before one of these is usually the preverbal element of a compound
# verb (`فرمان دادن`, `راهی شدن`, `تکان خوردن`), not an ezafe head, so the pair
# is suppressed.
_LIGHT_VERB_STEMS = frozenset({
    "become", "do", "make", "give", "strike", "hit", "beat", "take", "bring",
    "pull", "draw", "eat", "find", "get", "hold", "throw", "put",
})


def _gloss_labels(gloss: str) -> list[str]:
    """Split a Leipzig gloss into its labels (on `-`, `=`, and `.` boundaries)."""
    return [m for m in re.split(r"[-=.]", gloss) if m]


def _tok_gloss(tok: dict) -> str:
    return (tok.get("gloss") or {}).get("gloss", "")


def _token_has_ezafe(tok: dict) -> bool:
    """True when a token already carries ezafe — editorially (`"e": true`), in the
    interlinear gloss (an `EZ` clitic), or orthographically.

    Orthographic ezafe is visible (and the publisher writes it) on:
      - `ۀ`  he-ye ezafe on silent-`ه` words (`نگاشتۀ`, `همۀ`)
      - `ِ`  an explicit kasra
      - `های` plural + ezafe (the `ی` *is* the ezafe) — covers both fused nouns
        (`ورقه‌های`, `چیزهای`) and the standalone plural clitic token `های`
    The orthographic test is also robust to a mis-authored gloss (it does not
    rely on the `EZ` label being present)."""
    if tok.get("e"):
        return True
    if "EZ" in _gloss_labels(_tok_gloss(tok)):
        return True
    fa = tok.get("fa", "")
    return fa.endswith(("ۀ", "ِ", "های"))


def _is_verbal(tok: dict) -> bool:
    """True when the token's gloss carries any verb-form label."""
    return any(m in _VERBAL_TAGS for m in _gloss_labels(_tok_gloss(tok)))


def _is_light_verb(tok: dict) -> bool:
    """True for a verb token whose English stem is a common light-verb operator."""
    labels = _gloss_labels(_tok_gloss(tok))
    return (any(m in _VERBAL_TAGS for m in labels)
            and any(m in _LIGHT_VERB_STEMS for m in labels))


def _is_copula(tok: dict) -> bool:
    """True for a copula token (`است`, `بود`, `باشد`, `هست`)."""
    labels = _gloss_labels(_tok_gloss(tok))
    return "COP" in labels or "be" in labels


def _next_verb(toks: list, i: int) -> dict | None:
    """The next word token after index `i`, skipping the می/نمی prefix tokens that
    the publisher writes separately. Returns None if the next word is punctuation
    or the list ends."""
    j = i + 1
    while j < len(toks) and toks[j].get("fa") in _MI_PREFIX:
        j += 1
    tok = toks[j] if j < len(toks) else None
    return tok if tok and "fa" in tok else None


def _is_clitic_tail(tok: dict) -> bool:
    """True for a standalone clitic token that continues a noun group and so can
    itself host the ezafe — e.g. the plural `های`/`ها` in `ورقه های برنجی`.
    Detected as a gloss of grammatical labels only (no lexical stem) that
    includes `PL`."""
    labels = _gloss_labels(_tok_gloss(tok))
    if not labels or "PL" not in labels:
        return False
    return all(m.isupper() or not m.isalpha() for m in labels)


def _object_marker_follows(toks: list, start: int) -> bool:
    """True if a `را` (ACC) marker appears within the same clause from `start`
    onward — i.e. before the next verb or punctuation.

    When it does, the noun phrase here is a marked direct object, so a bare noun
    that precedes it is the clause subject, not the ezafe head: `لابان دارایی ما
    را دید` is "Laban saw our property", not "*the property of Laban". Without
    this, subject + object pairs are the lint's main false positive."""
    for tok in toks[start:]:
        if "fa" not in tok:          # punctuation closes the clause
            return False
        if _is_verbal(tok):          # the verb closes the object region
            return False
        if tok["fa"] == "را" or "ACC" in _gloss_labels(_tok_gloss(tok)):
            return True
    return False


def _lint_ezafe(source: dict, word_map: dict, pos_map: dict, label: str) -> None:
    """Warn on adjacent nominals with no ezafe between them (likely missing ezafe).

    Findings are aggregated by word pair (like the `unlinked` lint) and printed
    to stderr with the verses they occur in.
    """
    findings: dict[tuple[str, str], list[str]] = {}

    for sec in source.get("sections", []):
        if _section_type(sec) not in ("verse", "chapter-summary"):
            continue
        toks = sec.get("tokens") or []
        loc = _section_heading(sec)[1]
        for i in range(len(toks) - 1):
            a, b = toks[i], toks[i + 1]
            # Punctuation is its own token, so it breaks adjacency for us.
            if "fa" not in a or "fa" not in b:
                continue
            if _token_has_ezafe(a) or _is_verbal(a) or _is_verbal(b):
                continue
            # B must be a real lexical modifier (noun / proper noun / adjective).
            b_pos = _resolve_anchor(b.get("lemma") or b["fa"], pos_map)
            if b_pos not in _EZAFE_MOD_POS:
                continue
            # A must be able to host the ezafe: a head noun, or a plural clitic
            # tail continuing a preceding noun group.
            if (_resolve_anchor(a.get("lemma") or a["fa"], pos_map) not in _EZAFE_HEAD_POS
                    and not _is_clitic_tail(a)):
                continue
            # The verb following B reclassifies the A–B pair, not an ezafe phrase:
            #   • B + light verb  → compound verb (`فرمان داده`, `راهی شد`)
            #   • adjective + copula → predicate adjective (`لابان خشمگین بود`)
            vtok = _next_verb(toks, i + 1)
            if vtok and (_is_light_verb(vtok) or (b_pos == "adj" and _is_copula(vtok))):
                continue
            # B's phrase is a را-marked direct object → A is the subject, not an
            # ezafe head.
            if _object_marker_follows(toks, i + 2):
                continue
            # Skip components of one multiword lexeme (compound verb, fixed
            # phrase): both tokens resolve to the same vocab entry.
            a_anchor = _resolve_anchor(a.get("lemma") or a["fa"], word_map)
            if a_anchor and a_anchor == _resolve_anchor(b.get("lemma") or b["fa"], word_map):
                continue
            findings.setdefault((a["fa"], b["fa"]), []).append(loc)

    for (a_fa, b_fa), locs in sorted(findings.items(), key=lambda kv: -len(kv[1])):
        count = f" (×{len(locs)})" if len(locs) > 1 else ""
        uniq = ", ".join(dict.fromkeys(locs))
        print(f"  {label}possible missing ezafe: {a_fa} → {b_fa}{count} — {uniq}",
              file=sys.stderr)


# ---------- gloss/token alignment lint ----------
#
# Each token's `gloss.src` is a romanization of its `fa`, so the two should share
# the same leading consonant. When a clitic (`اش`, `را`, …) is split into its own
# `fa` token but glossed as part of the previous fused word, every following
# gloss shifts by one and the `src` values stop matching their `fa`. A run of
# consecutive consonant mismatches is a strong signal of such a shift (isolated
# transliteration quirks never form runs — see calibration in the commit).

# Persian *strong* (unambiguous) consonants → a coarse Latin class. Vowels and
# the ambiguous/weak letters (ا آ و ی ه ع ء) are deliberately omitted so they
# never drive the comparison.
_FA_CONSONANT = {
    "ب": "b", "پ": "p", "ت": "t", "ط": "t", "د": "d", "ج": "j", "چ": "c",
    "خ": "x", "ر": "r", "ز": "z", "ژ": "z", "س": "s", "ش": "s", "ص": "s",
    "ض": "z", "ث": "s", "ذ": "z", "ظ": "z", "ف": "f", "ق": "q", "غ": "q",
    "ک": "k", "ك": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n",
}
# Latin letters used in `src` → the same classes. Includes the scholarly
# transliteration variants (ṭ ṣ ẓ ż ṡ ṯ ḏ ġ …); the weak/neutral romanizations
# (ḥ for ح, ʿ ʾ for ع ء) are intentionally absent, mirroring the omitted Persian
# letters above.
_SRC_CONSONANT = {
    "b": "b", "p": "p", "t": "t", "ṭ": "t", "d": "d", "j": "j", "ǰ": "j",
    "č": "c", "c": "c", "x": "x", "r": "r", "z": "z", "ž": "z", "ż": "z", "ẓ": "z",
    "ḏ": "z", "s": "s", "š": "s", "ṣ": "s", "ṡ": "s", "ṯ": "s", "f": "f",
    "q": "q", "ğ": "q", "ġ": "q", "k": "k", "g": "g", "l": "l", "m": "m",
    "n": "n",
}
# A run this long of consecutive consonant mismatches flags the section. Clean
# sections never exceed 1; real shifts produce runs of 5–25.
_MISALIGN_RUN = 3


def _lead_consonant(text: str, table: dict[str, str]) -> str | None:
    """First strong consonant class in `text` per `table`, or None if it has none."""
    for ch in text.lower():
        if ch in table:
            return table[ch]
    return None


def _lint_gloss_alignment(source: dict, label: str) -> None:
    """Warn when a section's `gloss` objects look shifted off their `fa` tokens.

    Walks each section's word tokens and counts the longest run of consecutive
    tokens whose `fa` and `gloss.src` disagree on their leading consonant.
    Tokens with no comparable consonant on either side are neutral (skipped,
    they neither extend nor break a run)."""
    for sec in source.get("sections", []):
        toks = sec.get("tokens") or []
        run = max_run = 0
        start = max_start = None
        for tok in toks:
            if "fa" not in tok:
                continue
            fa_c = _lead_consonant(tok["fa"], _FA_CONSONANT)
            src_c = _lead_consonant((tok.get("gloss") or {}).get("src", ""), _SRC_CONSONANT)
            if fa_c is None or src_c is None:
                continue  # neutral — can't compare this token
            if fa_c == src_c:
                run = 0
                start = None
            else:
                if run == 0:
                    start = tok
                run += 1
                if run > max_run:
                    max_run, max_start = run, start

        if max_run >= _MISALIGN_RUN and max_start is not None:
            loc = _section_heading(sec)[1]
            bad_src = (max_start.get("gloss") or {}).get("src", "")
            print(f"  {label}gloss/token misalignment: {loc} — {max_run} consecutive "
                  f"tokens whose gloss src is off (near `{max_start['fa']}`, "
                  f"glossed `{bad_src}`)", file=sys.stderr)


# ---------- main renderer ----------

def render_chapter(
    source: dict,
    study: dict,
    css_href: str = "../styles.css",
    source_name: str = "",
    prev: tuple[str, str] | None = None,
    next: tuple[str, str] | None = None,
) -> str:
    """Render chapter source + study JSON to a complete HTML document string."""
    word_map = _build_vocab_map_json(study)
    pos_map = _build_pos_map_json(study)
    arabic_href = css_href.replace("styles.css", "arabic.html")
    unlinked: list[tuple[str, str]] = []

    book = study.get("book", "")
    chapter = study.get("chapter", "")
    title = f"{book} {chapter} — Persian Study Guide" if book and chapter else "Persian Study Guide"
    title_slug = _slug(title)

    # Index study sections by (type, number) for O(1) lookup
    study_index: dict[tuple[str, int | None], dict] = {}
    for s in study.get("sections", []):
        key = (_section_type(s), s.get("number"))
        study_index[key] = s

    # ------------------------------------------------------------------ #
    #  Lint — source.json checks                                         #
    # ------------------------------------------------------------------ #
    label = f"{source_name}: " if source_name else ""
    for source_sec in source.get("sections", []):
        t = _section_type(source_sec)
        n = source_sec.get("number")
        sec_desc = f"verse {n}" if n is not None else t

        # Every source section needs a matching study section.
        if (t, n) not in study_index:
            print(f"  {label}missing study section: {sec_desc}", file=sys.stderr)

        # Verse and chapter-summary sections must have tokens.
        tokens = source_sec.get("tokens")
        if t in ("verse", "chapter-summary") and not tokens:
            print(f"  {label}missing tokens: {sec_desc}", file=sys.stderr)

        # Verse sections need an English translation.
        if t == "verse" and not source_sec.get("en"):
            print(f"  {label}missing translation: verse {n}", file=sys.stderr)

        # Every word token must carry a gloss with both `src` and `gloss` keys.
        for tok in tokens or []:
            if "fa" not in tok:
                continue  # punctuation token — no gloss required
            fa = tok["fa"]
            g = tok.get("gloss")
            if g is None:
                print(f"  {label}token missing gloss: `{fa}` in {sec_desc}", file=sys.stderr)
            else:
                if not g.get("src"):
                    print(f"  {label}gloss missing src: `{fa}` in {sec_desc}", file=sys.stderr)
                if not g.get("gloss"):
                    print(f"  {label}gloss missing gloss field: `{fa}` in {sec_desc}", file=sys.stderr)

    # Heuristic: flag adjacent nominals with no ezafe between them.
    _lint_ezafe(source, word_map, pos_map, label)

    # Flag sections whose gloss objects have shifted off their fa tokens.
    _lint_gloss_alignment(source, label)

    body_parts: list[str] = [
        f'<h1 id="{title_slug}">{html_lib.escape(title)}</h1>',
        _build_chapter_toc(source, study),
    ]

    intro = re.sub(r"^#{1,3}\s+intro\s*\n?", "", study.get("intro", ""), flags=re.IGNORECASE).strip()
    if intro:
        body_parts.append('<h2 id="intro">Intro</h2>')
        body_parts.append(_render_prose(intro, word_map))

    reading_tip = study.get("reading_tip", "").strip()
    if reading_tip:
        body_parts.append('<h2 id="reading-tips">Reading tips</h2>')
        body_parts.append(_render_prose(reading_tip, word_map))

    if intro or reading_tip:
        body_parts.append("<hr>")

    body_parts.append('<h2 id="vocabulary-and-grammar">Vocabulary and Grammar</h2>')

    vocab_intro = study.get("vocab_intro", "")
    if vocab_intro:
        body_parts.append(_render_prose(vocab_intro, word_map=None))

    book_summary_emitted = False
    for source_sec in source.get("sections", []):
        t = _section_type(source_sec)
        n = source_sec.get("number")

        # Emit Book summary H3 heading before the first book-summary-* section
        if t in _BOOK_SUMMARY_TYPES and not book_summary_emitted:
            book_summary_emitted = True
            body_parts.append('<h3 id="book-summary">Book summary</h3>')
            bs_intro = study.get("book_summary_intro", "")
            if bs_intro:
                body_parts.append(_render_prose(bs_intro, word_map=None))

        study_sec = study_index.get((t, n))
        body_parts.append(_render_section(source_sec, study_sec, word_map, unlinked, arabic_href))


    body = "\n".join(body_parts)

    if unlinked:
        word_locs: dict[str, list[str]] = {}
        for word, loc in unlinked:
            word_locs.setdefault(word, []).append(loc)
        for word in sorted(word_locs, key=lambda w: -len(word_locs[w])):
            locs = word_locs[word]
            count_str = f" (×{len(locs)})" if len(locs) > 1 else ""
            unique_locs = list(dict.fromkeys(locs))
            loc_str = f" — {', '.join(unique_locs)}" if any(unique_locs) else ""
            print(f"  {label}unlinked: {word}{count_str}{loc_str}", file=sys.stderr)

    # Lint: vocab ordering — each headword entry should sit in the study section
    # that corresponds to where its lemma first appears in the source text.
    source_secs_ordered = source.get("sections", [])
    source_sec_rank: dict[tuple, int] = {
        (_section_type(s), s.get("number")): i
        for i, s in enumerate(source_secs_ordered)
    }

    # Walk source tokens in order; record the first section rank where each
    # vocab anchor is resolved.
    entry_first_rank: dict[str, int] = {}
    for sec in source_secs_ordered:
        sec_key = (_section_type(sec), sec.get("number"))
        rank = source_sec_rank[sec_key]
        tok_list = list(sec.get("tokens", []))
        i = 0
        while i < len(tok_list):
            tok = tok_list[i]
            if "fa" not in tok:
                i += 1
                continue
            fa = tok["fa"]
            lookup_key = tok.get("lemma") or fa
            # می/نمی: resolve against the following verb token, matching render logic
            if fa in _MI_PREFIX and i + 1 < len(tok_list) and "fa" in tok_list[i + 1]:
                nxt = tok_list[i + 1]
                nxt_key = nxt.get("lemma") or nxt["fa"]
                anchor = _resolve_anchor(nxt_key, word_map) or _resolve_anchor(nxt["fa"], word_map)
                if anchor and anchor not in entry_first_rank:
                    entry_first_rank[anchor] = rank
                i += 2
                continue
            anchor = _resolve_anchor(lookup_key, word_map)
            if anchor is None and lookup_key != fa:
                anchor = _resolve_anchor(fa, word_map)
            if anchor and anchor not in entry_first_rank:
                entry_first_rank[anchor] = rank
            i += 1

    for study_sec in study.get("sections", []):
        study_key = (_section_type(study_sec), study_sec.get("number"))
        study_rank = source_sec_rank.get(study_key)
        if study_rank is None:
            continue
        for entry in study_sec.get("entries", []):
            if entry.get("type") != "headword":
                continue
            persian = entry.get("persian", "")
            entry_id = entry.get("id") or persian.replace(" ", "_")
            anchor = f"vocab-{entry_id}"
            first_rank = entry_first_rank.get(anchor)
            if first_rank is None or first_rank == study_rank:
                continue
            _, first_heading, _ = _section_heading(source_secs_ordered[first_rank])
            _, study_heading, _ = _section_heading(study_sec)
            direction = "too late" if study_rank > first_rank else "too early"
            print(
                f"  {label}vocab order: '{persian}' first appears in {first_heading}"
                f" but entry is in {study_heading} ({direction})",
                file=sys.stderr,
            )

    # Warn about entries with a `root` field but no `arabic_form`
    for sec in study.get("sections", []):
        for entry in sec.get("entries", []):
            etym = entry.get("etym")
            if not isinstance(etym, dict):
                continue
            if etym.get("root") and not etym.get("arabic_form"):
                persian = entry.get("persian", "?")
                prose = etym.get("prose", "")
                print(
                    f"  {label}root without arabic_form: {persian} — {prose[:60]}",
                    file=sys.stderr,
                )

    # ------------------------------------------------------------------ #
    #  Lint — study.json checks                                          #
    # ------------------------------------------------------------------ #
    for sec in study.get("sections", []):
        for entry in sec.get("entries", []):
            etype = entry.get("type")

            # --- headword checks ---
            if etype == "headword":
                pos = entry.get("pos")
                persian = entry.get("persian", "?")

                # Required scalar fields
                if not entry.get("translit"):
                    print(f"  {label}headword missing translit: {persian}", file=sys.stderr)
                if not entry.get("meaning"):
                    print(f"  {label}headword missing meaning: {persian}", file=sys.stderr)
                if not pos:
                    print(f"  {label}headword missing pos: {persian}", file=sys.stderr)

                # POS-driven structural requirements
                if pos == "verb" and not entry.get("pres_stem"):
                    print(f"  {label}verb missing pres_stem: {persian}", file=sys.stderr)
                if pos == "verb" and entry.get("pres_stem"):
                    if not entry["pres_stem"].get("translit"):
                        print(f"  {label}pres_stem missing translit: {persian}", file=sys.stderr)
                if pos == "noun" and not entry.get("plural") and not entry.get("light_verb"):
                    print(f"  {label}noun missing plural: {persian}", file=sys.stderr)
                if pos == "noun" and entry.get("plural"):
                    pl = entry["plural"]
                    if not pl.get("suffixes") and not pl.get("broken"):
                        print(f"  {label}plural has no forms: {persian}", file=sys.stderr)

                # etym.arabic_form must be a known value
                etym = entry.get("etym")
                if isinstance(etym, dict) and etym.get("arabic_form"):
                    af = etym["arabic_form"]
                    if af not in _ARABIC_FORM_ANCHORS:
                        print(
                            f"  {label}unknown arabic_form '{af}': {persian}",
                            file=sys.stderr,
                        )

            # --- variant checks ---
            elif etype == "variant":
                if not entry.get("persian"):
                    print(f"  {label}variant missing persian", file=sys.stderr)
                if not entry.get("meaning"):
                    vp = entry.get("persian", "?")
                    print(f"  {label}variant missing meaning: {vp}", file=sys.stderr)

            # --- grammar-note checks ---
            elif etype == "grammar-note":
                title = entry.get("title") or ""
                tag = f"'{title}'" if title else "(no title)"
                if not title:
                    print(f"  {label}grammar-note missing title", file=sys.stderr)
                if not entry.get("body"):
                    print(f"  {label}grammar-note missing body: {tag}", file=sys.stderr)
                examples = entry.get("examples") or []
                if not examples:
                    print(f"  {label}grammar-note missing examples: {tag}", file=sys.stderr)
                for i, ex in enumerate(examples):
                    ex_tag = f"{tag} example {i + 1}"
                    if not ex.get("ref"):
                        print(f"  {label}grammar-note example missing ref: {ex_tag}", file=sys.stderr)
                    if not ex.get("ref_anchor"):
                        print(f"  {label}grammar-note example missing ref_anchor: {ex_tag}", file=sys.stderr)
                    if not ex.get("persian"):
                        print(f"  {label}grammar-note example missing persian: {ex_tag}", file=sys.stderr)
                    if not ex.get("translit"):
                        print(f"  {label}grammar-note example missing translit: {ex_tag}", file=sys.stderr)

    index_href = str(Path(css_href).parent / ".." / "index.html")
    prev_slot = (
        f'<a href="{prev[0]}" class="nav-prev">← {html_lib.escape(prev[1])}</a>'
        if prev else '<span class="nav-spacer"></span>'
    )
    next_slot = (
        f'<a href="{next[0]}" class="nav-next">{html_lib.escape(next[1])} →</a>'
        if next else '<span class="nav-spacer"></span>'
    )
    up_slot = f'<a href="{index_href}" class="nav-up">↑ Study Guides</a>'
    nav = f'<nav class="up-nav">{prev_slot}{up_slot}{next_slot}</nav>'

    page_stem = Path(source_name).stem if source_name else ""
    body_class = f' class="page-{page_stem}"' if page_stem else ""

    return DOCUMENT.format(
        title=title,
        css=css_href,
        body=body,
        body_class=body_class,
        nav=nav,
    )


# ---------- CLI ----------

def main() -> int:
    if len(sys.argv) != 4:
        print(
            f"usage: {sys.argv[0]} <source.json> <study.json> <output.html>",
            file=sys.stderr,
        )
        return 2
    source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    study = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    out_path = Path(sys.argv[3])
    html = render_chapter(source, study, source_name=sys.argv[1])
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({len(html):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Migrate a chN.md study guide to chN.source.json + chN.study.json.

Usage:
    python3 migrate_md_to_json.py study_guide/01_nephi/ch2.md

Writes next to the input:
    chN.source.json  — pre-tokenised scripture text, interlinear gloss, English
    chN.study.json   — intro, vocab entries (headwords/variants), grammar notes

Raises ValueError (with 1-based line number) on any ambiguous or unrecognised
construct. Never warns-and-continues; every parse error is fatal.

KNOWN ch1.md issues that require manual pre-processing before running:
  1. Bare ';' line after a closing '>>>' (line 144 of ch1.md).
  2. A _Forms_: sub-bullet whose text is split across a grammar-note fence:
     شدن entry, lines 146-158 of ch1.md. Merge the Forms text onto one line
     and relocate the grammar note to appear after the full شدن entry.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Unicode helpers
# ---------------------------------------------------------------------------

_ARABIC_PUNCT = frozenset('،؛؟')   # Arabic/Persian punctuation that is NOT a letter


def _is_persian_char(c: str) -> bool:
    """True for Arabic/Persian letters, diacritics, digits; False for punctuation."""
    if c in _ARABIC_PUNCT:
        return False
    cp = ord(c)
    return (
        0x0600 <= cp <= 0x06FF       # Arabic block (letters, diacritics, digits)
        or c == '‌'             # ZWNJ
        or 0xfe70 <= cp <= 0xfeff   # Arabic Presentation Forms
    )


# ---------------------------------------------------------------------------
# Source-text tokenisation
# ---------------------------------------------------------------------------

def _split_word(word: str, line_num: int, ezafe: bool) -> list[dict]:
    """Split one whitespace-free token into leading-punct + arabic-core + trailing-punct."""
    first = next((i for i, c in enumerate(word) if _is_persian_char(c)), None)
    if first is None:
        return [{"p": word}]
    last = len(word) - 1 - next(
        idx for idx, c in enumerate(reversed(word)) if _is_persian_char(c)
    )
    leading  = word[:first]
    core     = word[first : last + 1]
    trailing = word[last + 1:]
    toks: list[dict] = []
    if leading:
        toks.append({"p": leading})
    tok: dict = {"fa": core}
    if ezafe:
        tok["e"] = True
    toks.append(tok)
    if trailing:
        toks.append({"p": trailing})
    return toks


def _tokenize_source(raw: str, line_num: int) -> list[dict]:
    """Tokenise the content inside a backtick source-text line."""
    tokens: list[dict] = []
    for word in raw.split():
        if word.endswith('{e}'):
            tokens.extend(_split_word(word[:-3], line_num, ezafe=True))
        else:
            tokens.extend(_split_word(word, line_num, ezafe=False))
    return tokens


# ---------------------------------------------------------------------------
# Gloss parsing
# ---------------------------------------------------------------------------

def _parse_gloss(text: str, line_num: int) -> list[dict]:
    """Parse the payload after '[gloss] ' into [{src, gloss}, ...]."""
    result: list[dict] = []
    for tok in text.split():
        parts = tok.split('|')
        if len(parts) != 2:
            raise ValueError(
                f"line {line_num}: gloss token has {len(parts) - 1} pipe(s), "
                f"expected exactly 1: {tok!r}"
            )
        result.append({"src": parts[0], "gloss": parts[1]})
    return result


# ---------------------------------------------------------------------------
# Forms parsing
# ---------------------------------------------------------------------------

def _split_forms_clauses(text: str) -> list[str]:
    """Split forms text on '; ' at bracket/paren nesting depth 0."""
    clauses: list[str] = []
    buf: list[str]     = []
    depth = 0
    i     = 0
    while i < len(text):
        c = text[i]
        if c in '([':
            depth += 1
            buf.append(c)
        elif c in ')]':
            depth -= 1
            buf.append(c)
        elif c == ';' and depth == 0 and i + 1 < len(text) and text[i + 1] == ' ':
            s = ''.join(buf).strip()
            if s:
                clauses.append(s)
            buf = []
            i += 2
            continue
        else:
            buf.append(c)
        i += 1
    last = ''.join(buf).strip()
    if last:
        clauses.append(last)
    return clauses


_BACKTICK_RE = re.compile(r'`([^`]*)`')


def _parse_forms_clause(clause: str, line_num: int) -> dict:
    """Parse one forms clause into {fa, desc} or {note}."""
    matches  = list(_BACKTICK_RE.finditer(clause))
    persian  = [(m.start(), m.end(), m.group(1))
                for m in matches if any(_is_persian_char(c) for c in m.group(1))]
    if not persian:
        return {"note": clause}

    # Collect the first contiguous run of adjacent Persian backtick groups.
    group = [persian[0]]
    for pm in persian[1:]:
        between = clause[group[-1][1] : pm[0]]
        if between.strip() == '':
            group.append(pm)
        else:
            break  # non-adjacent; stop
    fa = ' '.join(t for _, _, t in group)
    # Store the entire clause as `desc` so the renderer can detect the
    # embedded backtick-wrapped fa and render migration-style (just _inline).
    return {"fa": fa, "desc": clause}


def _parse_forms(text: str, line_num: int) -> list[dict]:
    """Parse the payload after '_Forms_: '."""
    text = text.strip().rstrip('.')
    return [_parse_forms_clause(c, line_num) for c in _split_forms_clauses(text) if c]


# ---------------------------------------------------------------------------
# Headword line parsing
# ---------------------------------------------------------------------------

_BOLD_RE      = re.compile(r'^\*\*(.+?)\*\*')
_ITALIC_RE    = re.compile(r'^_((?:[^_]|(?<=\\)_)+?)_')
_TAG_ONLY_RE  = re.compile(r'^\s*\[([^\]]+)\]\s*$')
_PRES_STEM_RE = re.compile(r'^\(pres\.\s+_((?:[^_]|\\_)+?)_\)')


def _parse_headword_line(line: str, line_num: int) -> dict:
    """Parse '- **persian** [tag] — _translit_ [(pres. _stem_)] [tag] — meaning'."""
    text  = line[2:].strip()   # strip leading '- '
    parts = text.split(' — ', 2)
    if len(parts) != 3:
        raise ValueError(
            f"line {line_num}: headword needs exactly 3 ' — '-separated fields, "
            f"got {len(parts)}: {text!r}"
        )
    persian_part, translit_part, meaning_part = [p.strip() for p in parts]

    # Persian field: **word** optional [tag]
    bm = _BOLD_RE.match(persian_part)
    if not bm:
        raise ValueError(f"line {line_num}: no **bold** in persian field: {persian_part!r}")
    persian    = bm.group(1)
    after_bold = persian_part[bm.end():].strip()
    tags: list[str] = []
    if after_bold:
        tm = _TAG_ONLY_RE.match(after_bold)
        if tm:
            tags.append(tm.group(1).lower().replace(' ', '-'))
        else:
            raise ValueError(
                f"line {line_num}: unexpected text after **{persian}**: {after_bold!r}"
            )

    # Translit field: _translit_ optional (pres. _stem_) optional [tag]
    im = _ITALIC_RE.match(translit_part)
    if not im:
        raise ValueError(
            f"line {line_num}: no _italic_ in translit field: {translit_part!r}"
        )
    translit  = im.group(1)
    after_tr  = translit_part[im.end():].strip()
    pres_stem = None
    psm = _PRES_STEM_RE.match(after_tr)
    if psm:
        pres_stem = {"fa": None, "translit": psm.group(1)}
        after_tr  = after_tr[psm.end():].strip()
    if after_tr:
        tm2 = _TAG_ONLY_RE.match(after_tr)
        if tm2:
            tags.append(tm2.group(1).lower().replace(' ', '-'))
            after_tr = ''
    # Any remaining text (e.g. "(sometimes _va_)") is a translit annotation, not an error.
    if after_tr:
        translit = translit + ' ' + after_tr

    return {
        "type":      "headword",
        "id":        persian.replace(' ', '_'),
        "persian":   persian,
        "translit":  translit,
        "meaning":   meaning_part,
        "tags":      tags,
        "pres_stem": pres_stem,
        "warning":   None,
        "etym":      None,
        "family":    None,
        "forms":     None,
    }


# ---------------------------------------------------------------------------
# Variant line parsing
# ---------------------------------------------------------------------------

def _parse_variant_line(line: str, line_num: int) -> dict:
    """Parse '- `persian` (_translit_) — meaning'."""
    text = line[2:].strip()
    fm   = re.match(r'^`([^`]+)`', text)
    if not fm:
        raise ValueError(f"line {line_num}: variant line must start with backtick: {text!r}")
    persian = fm.group(1)
    rest    = text[fm.end():].strip()
    translit: str | None = None
    trm = re.match(r'^\(_((?:[^_]|\\_)+?)_\)', rest)
    if trm:
        translit = trm.group(1)
        rest     = rest[trm.end():].strip()
    if rest.startswith('— '):
        meaning = rest[2:]
    elif rest.startswith('—'):
        meaning = rest[1:].strip()
    else:
        raise ValueError(f"line {line_num}: variant line missing '— meaning': {text!r}")
    return {"type": "variant", "persian": persian, "translit": translit, "meaning": meaning}


# ---------------------------------------------------------------------------
# Grammar-note assembly
# ---------------------------------------------------------------------------

def _parse_example_group(lines: list[str]) -> dict:
    """Parse one group of '> ...' lines into an example dict."""
    stripped = [
        ln[2:] if ln.startswith('> ') else ('' if ln == '>' else ln)
        for ln in lines
    ]
    ref = ref_anchor = persian = translit = en = ''
    if stripped:
        first = stripped[0]
        rm    = re.match(r'^\[([^\]]+)\]\(#([^)]+)\):\s*', first)
        if rm:
            ref        = rm.group(1)
            ref_anchor = rm.group(2)
            remainder  = first[rm.end():]
            btm = re.match(r'^`([^`]+)`', remainder)
            persian = btm.group(1) if btm else remainder
        else:
            persian = first
    if len(stripped) >= 2:
        t        = stripped[1]
        translit = t[1:-1] if (t.startswith('_') and t.endswith('_')) else t
    if len(stripped) >= 3:
        en = stripped[2]
    return {"ref": ref, "ref_anchor": ref_anchor, "persian": persian,
            "translit": translit, "en": en}


def _build_grammar_note(title: str, body_lines: list[str]) -> dict:
    """Assemble a grammar-note entry dict from its collected raw lines."""
    # Segment body_lines into 'text' runs and '>' groups.
    segments: list[tuple[str, object]] = []
    i = 0
    while i < len(body_lines):
        ln = body_lines[i]
        if ln.startswith('> ') or ln == '>':
            group: list[str] = []
            while i < len(body_lines) and (body_lines[i].startswith('> ') or body_lines[i] == '>'):
                group.append(body_lines[i])
                i += 1
            segments.append(('quote', group))
        else:
            segments.append(('text', ln))
            i += 1

    quote_idxs = [j for j, (k, _) in enumerate(segments) if k == 'quote']
    examples: list[dict] = []

    if not quote_idxs:
        body_parts    = [c for k, c in segments if k == 'text']
        closing_parts: list[str] = []
    else:
        first_q       = quote_idxs[0]
        last_q        = quote_idxs[-1]
        body_parts    = [c for k, c in segments[:first_q]     if k == 'text']
        closing_parts = [c for k, c in segments[last_q + 1:]  if k == 'text']
        for qi in quote_idxs:
            examples.append(_parse_example_group(segments[qi][1]))

    body    = '\n'.join(str(l).rstrip() for l in body_parts).strip()
    closing = '\n'.join(str(l).rstrip() for l in closing_parts).strip()

    note: dict = {"type": "grammar-note", "title": title, "body": body, "examples": examples}
    if closing:
        note["closing"] = closing
    return note


# ---------------------------------------------------------------------------
# Section-heading detection
# ---------------------------------------------------------------------------

_VERSE_RE    = re.compile(r'^#{2,4} Verse (\d+)\s*$')
_SENTENCE_RE = re.compile(r'^#### Sentence (\d+)\s*$')


def _detect_section(line: str) -> dict | None:
    """Return {type, number} for a recognised data section heading, else None."""
    if line == '### Chapter summary':
        return {"type": "chapter-summary", "number": None}
    m = _VERSE_RE.match(line)
    if m:
        return {"type": "verse", "number": int(m.group(1))}
    if line == '#### Title':
        return {"type": "book-summary-title", "number": None}
    if line == '#### Subtitle':
        return {"type": "book-summary-subtitle", "number": None}
    m2 = _SENTENCE_RE.match(line)
    if m2:
        return {"type": "book-summary-sentence", "number": int(m2.group(1))}
    return None


# ---------------------------------------------------------------------------
# Main migration parser
# ---------------------------------------------------------------------------

def migrate(md_path: Path) -> tuple[dict, dict]:
    """Parse chN.md and return (source_dict, study_dict)."""
    raw_lines = md_path.read_text(encoding='utf-8').splitlines()

    book    = ''
    chapter = 0

    intro_parts:      list[str] = []
    vocab_preamble:   list[str] = []
    bk_summary_intro: list[str] = []
    closing_parts:    list[str] = []

    source_sections: list[dict] = []
    study_sections:  list[dict] = []

    cur_src:       dict | None  = None
    cur_stu:       dict | None  = None
    cur_entries:   list[dict]   = []
    last_headword: dict | None  = None   # for attaching sub-bullets after grammar notes

    # Grammar-note accumulation
    in_grammar_note       = False
    gn_title_pending      = True   # True until first non-blank line is captured as title
    gn_title              = ''
    gn_body:  list[str]   = []

    state = 'PRE_TITLE'

    def E(lnum: int, msg: str) -> ValueError:
        return ValueError(f"line {lnum}: {msg}")

    def flush() -> None:
        nonlocal cur_src, cur_stu, cur_entries, last_headword
        if cur_src is not None:
            source_sections.append(cur_src)
        if cur_stu is not None:
            cur_stu["entries"] = cur_entries
            study_sections.append(cur_stu)
        cur_src = cur_stu = last_headword = None
        cur_entries = []

    def start(sec_type: str, number: int | None) -> None:
        nonlocal cur_src, cur_stu, cur_entries, last_headword
        flush()
        cur_src = {"type": sec_type}
        if number is not None:
            cur_src["number"] = number
        cur_stu = {"section_type": sec_type}
        if number is not None:
            cur_stu["number"] = number
        cur_entries  = []
        last_headword = None

    def attach_subbullet(field: str, text: str, lnum: int) -> None:
        if last_headword is None:
            raise E(lnum, f"sub-bullet _{field}_: with no preceding headword")
        if field == 'etym':
            last_headword['etym'] = text
        elif field == 'family':
            last_headword['family'] = text
        elif field == 'forms':
            last_headword['forms'] = _parse_forms(text, lnum)
        elif field == 'warning':
            last_headword['warning'] = text
        else:
            raise E(lnum, f"unrecognised sub-bullet field: {field!r}")

    for i, raw in enumerate(raw_lines):
        lnum = i + 1
        line = raw.rstrip()

        # ── Grammar-note collection ──────────────────────────────────────
        if in_grammar_note:
            if line.strip() == '>>>':
                note = _build_grammar_note(gn_title, gn_body)
                cur_entries.append(note)
                in_grammar_note = False
                gn_title_pending = True
                gn_title = ''
                gn_body  = []
            elif gn_title_pending:
                if line.strip():
                    gn_title         = line.strip()
                    gn_title_pending = False
                # else: blank line before title — skip
            else:
                gn_body.append(line)
            continue

        # ── State dispatch ───────────────────────────────────────────────

        if state == 'PRE_TITLE':
            if line.startswith('# '):
                m = re.match(r'^# (\d+) Nephi (\d+)\s*—\s*Persian Study Guide\s*$', line)
                if not m:
                    raise E(lnum, f"unexpected H1 format: {line!r}")
                book    = f"{m.group(1)} Nephi"
                chapter = int(m.group(2))
                state   = 'IN_INTRO'
            continue

        if state == 'IN_INTRO':
            if line.startswith('## Vocabulary'):
                state = 'IN_VOCAB_PRE'
            elif line == '---' or not line.strip():
                pass   # separator / blank — skip
            else:
                intro_parts.append(line)
            continue

        if state == 'IN_VOCAB_PRE':
            if not line.strip() or line == '---':
                pass
            elif line == '### Book summary':
                state = 'IN_BK_SUM_INTRO'
            elif line.startswith('### ') or line.startswith('#### '):
                sec = _detect_section(line)
                if sec is None:
                    raise E(lnum, f"unrecognised section heading in vocab preamble: {line!r}")
                start(sec['type'], sec['number'])
                state = 'NEED_SOURCE'
            elif line.startswith('## '):
                raise E(lnum, f"unexpected ## heading in vocab preamble: {line!r}")
            else:
                vocab_preamble.append(line)
            continue

        if state == 'IN_BK_SUM_INTRO':
            if not line.strip() or line == '---':
                pass
            elif line.startswith('#### ') or line.startswith('### '):
                sec = _detect_section(line)
                if sec is None:
                    raise E(lnum, f"unrecognised heading in book-summary intro: {line!r}")
                start(sec['type'], sec['number'])
                state = 'NEED_SOURCE'
            else:
                bk_summary_intro.append(line)
            continue

        if state == 'NEED_SOURCE':
            if not line.strip() or line == '---':
                pass
            elif line.startswith('`') and line.endswith('`') and len(line) > 2:
                cur_src['tokens'] = _tokenize_source(line[1:-1], lnum)
                state = 'NEED_GLOSS'
            else:
                raise E(lnum, f"expected backtick source-text line, got: {line!r}")
            continue

        if state == 'NEED_GLOSS':
            if not line.strip():
                pass
            elif line.startswith('[gloss] '):
                cur_src['gloss'] = _parse_gloss(line[8:], lnum)
                state = 'NEED_EN'
            else:
                raise E(lnum, f"expected [gloss] line, got: {line!r}")
            continue

        if state == 'NEED_EN':
            if not line.strip():
                pass
            elif line.startswith('[en] '):
                cur_src['en'] = line[5:]
                state = 'IN_ENTRIES'
            else:
                raise E(lnum, f"expected [en] line, got: {line!r}")
            continue

        if state == 'AFTER_SECTIONS':
            if not line.strip() or line == '---':
                pass
            elif line.startswith('## A final note'):
                state = 'IN_CLOSING'
            elif line.startswith('## '):
                raise E(lnum, f"unexpected ## heading after all sections: {line!r}")
            else:
                raise E(lnum, f"unexpected content between sections and closing: {line!r}")
            continue

        if state == 'IN_CLOSING':
            closing_parts.append(line)
            continue

        if state == 'IN_ENTRIES':
            if not line.strip():
                continue

            # Section transition headings
            if line.startswith('#'):
                if line.startswith('## A final note'):
                    flush()
                    state = 'IN_CLOSING'
                    continue
                sec = _detect_section(line)
                if sec:
                    start(sec['type'], sec['number'])
                    state = 'NEED_SOURCE'
                    continue
                raise E(lnum, f"unrecognised heading in entries: {line!r}")

            if line == '---':
                # Separator before the closing section
                flush()
                state = 'AFTER_SECTIONS'
                continue

            # Grammar-note fence
            if line.strip() == '>>>':
                in_grammar_note  = True
                gn_title_pending = True
                gn_title         = ''
                gn_body          = []
                continue

            # No-new-lemmas marker
            if re.match(r'_\(No new lemm', line):
                cur_entries.append({"type": "no-new-lemmas"})
                continue

            # Sub-bullet (2-space indent)
            if line.startswith('  - '):
                sub = line[4:].strip()
                if sub.startswith('_Etym_:') or sub.startswith('_Etym._:'):
                    attach_subbullet('etym', sub.split(':', 1)[1].strip(), lnum)
                elif sub.startswith('_Family_:'):
                    attach_subbullet('family', sub[9:].strip(), lnum)
                elif sub.startswith('_Forms_:'):
                    attach_subbullet('forms', sub[8:].strip(), lnum)
                elif sub.startswith('⚠'):
                    attach_subbullet('warning', re.sub(r'^⚠️?\s*', '', sub), lnum)
                else:
                    raise E(lnum, f"unrecognised sub-bullet: {line!r}")
                continue

            # Headword entry
            if line.startswith('- **'):
                entry         = _parse_headword_line(line, lnum)
                cur_entries.append(entry)
                last_headword = entry
                continue

            # Variant entry
            if line.startswith('- `'):
                entry = _parse_variant_line(line, lnum)
                cur_entries.append(entry)
                last_headword = None   # variants don't receive sub-bullets
                continue

            raise E(
                lnum,
                f"unrecognised line in entries context: {line!r}\n"
                f"  Hint: if this is a continuation of a _Forms_: sub-bullet split\n"
                f"  across a grammar-note fence, merge the Forms text onto one line\n"
                f"  and move the grammar note to after the full entry."
            )

    flush()

    # ── Assemble output dicts ────────────────────────────────────────────
    source: dict = {
        "book":     book,
        "chapter":  chapter,
        "sections": source_sections,
    }
    study: dict = {
        "book":     book,
        "chapter":  chapter,
        "sections": study_sections,
    }
    if intro_text := '\n'.join(intro_parts).strip():
        study["intro"] = intro_text
    if vp := '\n'.join(vocab_preamble).strip():
        study["vocab_intro"] = vp
    if bsi := '\n'.join(bk_summary_intro).strip():
        study["book_summary_intro"] = bsi
    if ct := '\n'.join(closing_parts).strip():
        study["closing"] = ct

    return source, study


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------

def _strip_nones(entry: dict) -> dict:
    """Remove None-valued keys from a study entry."""
    return {k: v for k, v in entry.items() if v is not None}


def _clean_study(study: dict) -> dict:
    """Return a copy of study with None-valued entry fields removed."""
    result = dict(study)
    result["sections"] = [
        {**sec, "entries": [_strip_nones(e) for e in sec.get("entries", [])]}
        for sec in study.get("sections", [])
    ]
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <chN.md>", file=sys.stderr)
        return 2
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"error: {md_path} not found", file=sys.stderr)
        return 1

    source, study = migrate(md_path)

    src_path = md_path.with_name(md_path.stem + '.source.json')
    stu_path = md_path.with_name(md_path.stem + '.study.json')

    src_path.write_text(json.dumps(source,            ensure_ascii=False, indent=2), encoding='utf-8')
    stu_path.write_text(json.dumps(_clean_study(study), ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"  {md_path.name} → {src_path.name} ({len(source['sections'])} source sections)", file=sys.stderr)
    print(f"  {md_path.name} → {stu_path.name} ({len(study['sections'])} study sections)", file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

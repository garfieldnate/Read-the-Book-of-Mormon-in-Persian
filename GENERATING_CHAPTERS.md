# How to Generate a Chapter Study Guide

These instructions are for Claude. Follow them exactly when creating a new chapter study guide.

---

## Overview

Each chapter requires two JSON source files (never edit the rendered `.md` output directly):

| File | Purpose |
|---|---|
| `chN.source.json` | Pre-tokenized scripture text: Persian tokens with interlinear gloss and English translation |
| `chN.study.json` | Vocabulary entries, grammar notes, intro prose |

Both live in `study_guide/NN_book/` (e.g. `study_guide/01_nephi/ch3.source.json`).

After editing JSON, regenerate with:
```
python3 render_json.py study_guide/01_nephi/ch3.source.json study_guide/01_nephi/ch3.study.json _site/study_guide/01_nephi/ch3.html
```
or regenerate the whole site with `python3 build_site.py`.

---

## The 32 KB Rule

**Claude responses are capped at ~32 KB.** Both JSON files for a chapter are typically 100–170 KB. You must generate them in chunks and write each chunk to disk immediately. Never try to produce an entire file in one response.

Chunking strategy:
- **source.json**: 3–5 verses per response; book-summary sentences in groups of 3–4.
- **study.json**: 2–3 verses per response; each verse with many entries may need its own response.

Use `Edit` to append new sections into a partially-written file, or write Python helper snippets that merge fragments — whichever keeps individual responses under the limit.

---

## Step-by-Step Workflow

### Step 1 — Fetch the raw text

```bash
.venv/bin/python fetch_chapter.py \
  https://www.churchofjesuschrist.org/study/scriptures/bofm/<book-slug>/<chapter>?lang=pes \
  -o study_guide/<book-dir>/ch<chapter>_raw.txt
```

| Placeholder | Example (1 Ne. 3) | Notes |
|---|---|---|
| `<book-slug>` | `1-ne` | URL slug used by the church site (e.g. `2-ne`, `mosiah`, `alma`, `ether`) |
| `<chapter>` | `3` | Chapter number (no leading zero) |
| `<book-dir>` | `01_nephi` | Directory under `study_guide/` (e.g. `02_nephi`, `07_mosiah`) |

Concrete example for 1 Nephi 3:
```bash
.venv/bin/python fetch_chapter.py \
  https://www.churchofjesuschrist.org/study/scriptures/bofm/1-ne/3?lang=pes \
  -o study_guide/01_nephi/ch3_raw.txt
```

This dumps labeled blocks: `# title`, `# subtitle`, `# intro`, `# chapter`, `# study-summary`, `# verse N`. Keep this file as your source of truth for the Persian text.

The `# intro` block (the book-level summary) only appears on chapter 1 of each book.

### Step 2 — Create `chN.source.json` (in chunks)

Build an array of sections matching the chapter structure. Write 3–5 sections at a time.

**File skeleton** (write this first):
```json
{
  "book": "1 Nephi",
  "chapter": 3,
  "sections": []
}
```

Then fill in `"sections"` incrementally.

### Step 3 — Create `chN.study.json` (in chunks)

Same structure but with `"section_type"` keys (not `"type"`) on each section, and `"entries"` arrays containing vocab and grammar content.

**File skeleton**:
```json
{
  "book": "1 Nephi",
  "chapter": 3,
  "intro": "",
  "sections": []
}
```

For every section in a chN.source.json there must be a matching section in its corresponding chN.study.json (same `section_type` + `number`). The renderer warns on stderr for mismatches.

### Step 4 — Render and check

```bash
python3 render_json.py \
  study_guide/01_nephi/ch3.source.json \
  study_guide/01_nephi/ch3.study.json \
  _site/study_guide/01_nephi/ch3.html
```

Fix any `unlinked:` or `missing study section:` warnings printed to stderr.

---

## JSON schemas and content rules

See **[CONTENT_RULES.md](CONTENT_RULES.md)** for the full JSON schemas (section types, token object, entry types, POS values, gloss abbreviations) and all editorial decisions (what to include, headword fields, `etym`/`family`/`forms`, grammar-note placement, numerals, ezafe marking, token registration, and more).

---

## Practical Chunking Example

For a 20-verse chapter, a safe work plan:

1. Write file skeletons for both JSON files.
2. **source.json**: verses 1–5 (one response), verses 6–10, 11–15, 16–20. Write each chunk immediately.
3. **source.json chapter-summary**: one response.
4. **study.json chapter-summary**: one response.
5. **study.json verses 1–3**: one response (expect ~8–12 headwords each).
6. Continue 2–3 verses at a time until done.
7. Run the renderer; fix warnings.

For chapter 1 of a new book, add 2–3 extra responses for the book-summary sections (title, subtitle, sentences 1–5; sentences 6–10; sentences 11–15).

---

## Running the Renderer

```bash
# Single chapter
python3 render_json.py \
  study_guide/01_nephi/ch3.source.json \
  study_guide/01_nephi/ch3.study.json \
  _site/study_guide/01_nephi/ch3.html

# Full site
python3 build_site.py
```

Warnings printed to stderr:
- `missing study section: verse 7` — add a section to study.json for verse 7.
- `unlinked: فلان (×3) — Verse 5, Verse 8` — the word appears in source tokens but has no vocab entry; add a headword or check the `id` field.
- `verb missing pres_stem: خواندن` — add `"pres_stem"` to that entry.
- `noun missing plural: کتاب` — add `"plural"` or `"light_verb"` to that entry.
- `vocab order: 'بسیار' first appears in Verse 4 but entry is in Verse 11 (too late)` — the headword entry is in the wrong study section. Move it to the section matching where it first appears in source. "too early" means the entry is before the word's first appearance; "too late" means after.

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

Fix any warnings printed to stderr (see the full list in the **Running the Renderer** section below). Once the render is clean, verify that all in-page anchor links resolve:

```bash
python3 check_links.py
```

`check_links.py` scans every HTML file in `_site/` and reports any `href="#…"` whose target `id="…"` does not exist in the same file. Fix broken links before pushing.

### Step 5 — Generate audio (optional, requires a paid ElevenLabs plan)

Each source section can have a text-to-speech player. Generate the audio once and commit it; the site build and CI never call the API.

```bash
.venv/bin/python generate_audio.py --source study_guide/01_nephi/ch3.source.json
# --dry-run to preview text + character cost first; --force to overwrite; --section verse-1 for one section
```

Requirements and behavior:
- **API key**: read from `.env` at the repo root, key name `11labsApiKey` (`.env` is gitignored — never commit it).
- **Paid plan required**: the voices (IMan for verses, Zara for summaries) are ElevenLabs *library* voices; the free tier rejects them over the API with **HTTP 402**. Model is `eleven_v3` (the only one that speaks Persian), billed 1 credit/char (~4,900 chars/chapter).
- **ffmpeg** must be on `PATH` (precomputes the waveform peaks).
- Voice is chosen automatically by section role (verse → male, summary → female). Verse numbers are spoken and set apart with a period; editorial ezafe is **not** sent to the engine.
- Outputs: `study_guide/audio/<book>/<chap>/<anchor>.{mp3,timing.json,peaks.json}`. Re-running skips sections that already exist (use `--force` to redo). After generating, re-run `build_site.py` so the players appear.

See the **Audio** section of `README.md` for the full asset flow.

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

# Verify all in-page anchor links resolve (run after build_site.py)
python3 check_links.py
```

Warnings printed to stderr:
- `missing study section: verse 7` — add a section to study.json for verse 7.
- `unlinked: فلان (×3) — Verse 5, Verse 8` — the word appears in source tokens but has no vocab entry; add a headword or check the `id` field.
- `verb missing pres_stem: خواندن` — add `"pres_stem"` to that entry.
- `noun missing plural: کتاب` — add `"plural"` or `"light_verb"` to that entry.
- `vocab order: 'بسیار' first appears in Verse 4 but entry is in Verse 11 (too late)` — the headword entry is in the wrong study section. Move it to the section matching where it first appears in source. "too early" means the entry is before the word's first appearance; "too late" means after.
- `possible missing ezafe: ورقه → برنجی — <location>` — **heuristic** check for unwritten editorial ezafe. A noun is directly followed by another noun/adjective with no ezafe marked between them, which usually means an `"e": true` (or, on a plural, the `ی` of `های`) was missed. Each finding is a candidate to **review, not auto-apply** — adjacent nominals can also be an unrelated subject + object (`لابان دارایی ما را دید` "Laban saw our property") or a fixed phrase (`از این رو` "therefore"), which are not ezafe sites. Add the ezafe if it belongs; otherwise ignore the line.
- `gloss/token misalignment: <location> — N consecutive tokens whose gloss src is off (near ...)` — the `gloss` objects have shifted out of step with the `fa` tokens, so each token shows a neighbour's gloss. This almost always happens when a clitic (`اش`, `را`, `ش`) is split into its own `fa` token but glossed as part of the previous fused word. For example, the fused gloss `xāne-aš` is left on the `خانه` token, so every later gloss is one slot early:

  ```json
  {"fa": "خانه", "gloss": {"src": "xāne-aš", "gloss": "house-3SG.POSS"}},
  {"fa": "اش",   "gloss": {"src": "rā",      "gloss": "ACC"}},
  {"fa": "را",   "gloss": {"src": "tark",    "gloss": "abandonment"}}
  ```

  Fix by giving the split-off clitic its own gloss and re-pairing the rest:

  ```json
  {"fa": "خانه", "gloss": {"src": "xāne",  "gloss": "house"}},
  {"fa": "اش",   "gloss": {"src": "-aš",   "gloss": "3SG.POSS"}},
  {"fa": "را",   "gloss": {"src": "rā",    "gloss": "ACC"}}
  ```

  The check is reliable — it does not fire on a clean section — so always fix these.
- `ezafe double-marked ("e": true on an already-ezafe form): های — <location>` — the token already shows ezafe in its spelling (`ۀ`, the `ی` of `های`, or an explicit kasra), so `"e": true` makes the renderer draw a second kasra. Remove the `"e"` flag (the spelling already carries the ezafe).
- `ezafe "e": true but gloss has no =EZ: مرد — <location>` — the rendered ezafe and the interlinear gloss disagree. If the word really takes ezafe, add the clitic to the gloss (`"src": "mard=e"`, `"gloss": "man=EZ"`); if not, drop the `"e"` flag.
- `duplicate anchor: vocab-…` — two headword/variant entries generate the same HTML anchor (a repeated `persian`/`id`), which collides their `id`s and breaks in-page links. Merge the entries or give one a distinct `id`.
- `headword translit mismatch: گنبد / gombad` — a headword's `translit` does not transliterate its `persian` (a consonant is missing or wrong), usually a typo. The `ن`→`m` assimilation before `ب/پ/م` is allowed, so this fires on genuine mismatches only.
- `grammar example bad ref_anchor: verse-99 (...)` — a grammar-note example's `ref_anchor` points at a section that doesn't exist; fix it to a real anchor (`verse-N`, `chapter-summary`, …).
- `grammar example not verbatim from source: فلان (...)` — a grammar-note example contains Persian words that do not appear in the chapter's source text (harakat ignored). Examples must be quoted verbatim from the chapter; correct the wording or pick a real phrase.

### Silencing false positives

The `possible missing ezafe` check is heuristic and will report some non-issues (subject + object, compound verbs, fixed phrases). Once you have **confirmed** a finding is not a real missing ezafe, record it in **`lint_ignore.json`** (repo root) so it stops being reported and the genuine findings stand out. Add an entry under the lint category and the `"<book> <chapter>"` key, with the `pair` copied exactly from the lint output and a short `reason`:

```json
"possible missing ezafe": {
  "1 Nephi 2": [
    {"pair": "پدرم → سخن", "reason": "پدرم + سخن گفت (my father spoke) — compound verb"}
  ]
}
```

Only suppress confirmed false positives — never a real issue you simply haven't fixed yet. See the file's `_README` for the full format.

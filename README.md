# Persian Book of Mormon Study Guides

Just want to study? View the study guide [here](https://nateglenn.com/Read-the-Book-of-Mormon-in-Persian/).

> This project is largely LLM-generated for my own study purposes. The README is mostly intended as instructions to an LLM for generating further study guides for the next chapters.

> I am just learning Persian myself, so if you see any errors or have suggestions for improvement, please open an issue or submit a PR!

A reusable setup for producing learner-oriented English study guides from a Persian translation of the Book of Mormon. Each chapter lives in `study_guide/NN_book/` — one directory per book. **The authoritative format for chapter content is a pair of JSON files** (`chN.source.json` + `chN.study.json`); see [GENERATING_CHAPTERS.md](GENERATING_CHAPTERS.md) and [CONTENT_RULES.md](CONTENT_RULES.md) for the full authoring guide.

```
.
├── README.md                   # this file — conventions and workflow
├── fetch_chapter.py            # download a chapter's clean text from churchofjesuschrist.org
├── render.py                   # Markdown → semantic HTML (used for reference pages only)
├── render_json.py              # JSON → semantic HTML (used for chapter pages)
├── build_site.py               # walks study_guide/NN_*/chN.{source,study}.json and builds _site/
├── migrate_md_to_json.py       # one-time migration tool (no longer needed)
├── check_links.py              # verify all in-page anchor links resolve
├── .github/workflows/
│   └── pages.yml               # CI: runs build_site.py and deploys to GitHub Pages
└── study_guide/                # all study material
    ├── styles.css              # shared stylesheet for all pages' HTML
    ├── transcription.md        # Persian transliteration scheme (standalone reference page)
    ├── verbs.md                # Persian verb conjugations (standalone reference page)
    ├── arabic.md               # Arabic borrowings in Persian (standalone reference page)
    └── NN_book/                # one directory per book (01_nephi, 02_nephi, 03_jacob, …)
        ├── ch1.source.json     # scripture text + interlinear gloss (source of truth)
        ├── ch1.study.json      # intro + vocab entries + grammar notes
        └── …
```

The directory prefix is the **book index** (01–15 in publication order: 1 Nephi, 2 Nephi, Jacob, Enos, …); the slug after the underscore is the book's English name (lowercased, words separated with `_`). `build_site.py` reads the title from the first H1 of `ch1.study.json`'s `intro` field (or falls back to `book + chapter`). It also renders the standalone Markdown reference pages linked from the index.

Rendered HTML is **not committed**. `build_site.py` produces `_site/` containing one HTML page per chapter plus `index.html` and `styles.css`; GitHub Actions runs the build on every push to `main`/`master` and publishes `_site/` to GitHub Pages. To preview locally:

```bash
python3 build_site.py
open _site/index.html        # or: python3 -m http.server -d _site
```

## Generating a new chapter

See **[GENERATING_CHAPTERS.md](GENERATING_CHAPTERS.md)** for the full step-by-step workflow: fetching the raw text, building the two JSON files in chunks, and running the renderer.

## JSON schema and content rules

Each chapter is two JSON files in `study_guide/NN_book/`:

- **`chN.source.json`** — tokenized scripture text with interlinear gloss (`gloss.src` / `gloss.gloss`) and English translation (`en`). Sections have `type` + optional `number`; token objects have `fa` (Persian), optional `e: true` for editorial ezafe, optional `p` for punctuation, and a required `gloss` sub-object on every word token.
- **`chN.study.json`** — `intro`, `reading_tip`, and `sections` (matched to source by `section_type` + `number`). Each section has an `entries` array of `headword`, `variant`, `grammar-note`, or `no-new-lemmas` objects.

All editorial decisions — required fields, POS values, `pres_stem`/`plural`/`light_verb`/`etym`/`forms` rules, grammar-note structure, numerals, ezafe marking, interlinear gloss abbreviations, and more — are documented in **[CONTENT_RULES.md](CONTENT_RULES.md)**.

`render_json.py` enforces these rules at build time and prints `stderr` warnings for every violation (missing glosses, missing translations, misordered vocab entries, unknown `arabic_form` values, etc.). Aim for a clean render with no warnings before pushing.

## Content conventions

### Transcription scheme

The full transliteration table, pronunciation notes, and diphthong guide live in `study_guide/transcription.md` (rendered as a standalone reference page at `_site/study_guide/transcription.html`).

## HTML rendering

**Chapter study guides** are rendered from JSON by `render_json.py`. **Reference pages** (`verbs.md`, `word_formation.md`, etc.) are rendered from Markdown by `render.py`. Both renderers share `styles.css` and produce the same HTML class taxonomy. `build_site.py` runs both renderers in sequence and emits a top-level `_site/index.html`.

```bash
python3 build_site.py                                                                     # full site → _site/
python3 render_json.py study_guide/NN_book/chN.source.json study_guide/NN_book/chN.study.json /tmp/x.html  # one chapter
python3 render.py study_guide/verbs.md /tmp/verbs.html                                   # one reference page
```

The HTML document structure is standard: `<main>` wraps the body; headings are `<h1>/<h2>/<h3>`; paragraphs are `<p>`; nested lists are rendered as properly-nested `<ul>/<li>`. The semantic elements unique to this project get classes from a small fixed taxonomy:

Both renderers produce the same CSS class taxonomy, documented here. The "Source" column notes whether the class is generated from JSON (chapter pipeline via `render_json.py`) or Markdown (reference-page pipeline via `render.py`).

| Class               | Applied to | Source | Notes |
| ------------------- | ---------- | ------ | ----- |
| `.vocab`            | `<ul>`     | Both   | Vocab list wrapper. |
| `.vocab-entry`      | `<li>`     | Both   | Gets `id="vocab-HEADWORD"` so `.src-link` anchors resolve. |
| `.vocab-meta`       | `<ul>`     | Both   | Sub-list for etym / forms / family. |
| `.vocab-etym`       | `<li>`     | Both   | From `etym` field (JSON) or `*Etym*` label (Markdown). |
| `.vocab-forms`      | `<li>`     | Both   | From `forms` array (JSON) or `*Forms*` label (Markdown). |
| `.vocab-family`     | `<li>`     | Both   | From `family` field (JSON) or `*Family*` label (Markdown). |
| `.vocab-meta-other` | `<li>`     | Both   | Fallback for unrecognized sub-bullet labels. |
| `.meta-label`       | `<span>`   | Both   | The `Etym` / `Forms` chip rendered as a small uppercase tag. |
| `.persian`          | `<strong>` | Both   | The Persian headword. |
| `.translit`         | `<em>`     | Both   | The romanization. |
| `.proper`           | `<span>`   | Both   | `[proper]` tag on proper-noun entries. |
| `.example`          | `<div>`    | Both   | Grammar example block (from `examples` array in JSON; from `> blockquote` in Markdown). |
| `.example-fa`       | `<div>`    | Both   | First line of an example — Persian. Uses `direction: ltr` so the `.line-ref` label sits on the left; the inner `<code>` uses `direction: rtl` so Persian still renders right-to-left. Do **not** change to `direction: rtl` — that reverses the label position. |
| `.example-tr`       | `<div>`    | Both   | Second line — italic transliteration. |
| `.example-en`       | `<div>`    | Both   | Third line — English translation. |
| `.line-ref`         | `<span>`   | Both   | Section-reference prefix (e.g. `[Verse 4](#verse-4):`). |
| `.source-text`      | `<p>`      | Both   | Block-display Persian source line. |
| `.src-link`         | `<a>`      | Both   | Persian token inside `.source-text` linked to its vocab entry. |
| `.translation`      | `<div>`    | Both   | English translation; hidden by default, shown via **Translation** toggle. |
| `.translation-en`   | `<div>`    | Both   | Official English (`en` field / `[en]` marker). |
| `.translation-lit`  | `<div>`    | Both   | Literal gloss (`[lit]` marker). |
| `.gloss`            | `<div>`    | Both   | Interlinear gloss block; hidden by default, shown via **Gloss** toggle. |
| `.gloss-words`      | `<div>`    | Both   | Flex container; words flow left-to-right. |
| `.gloss-unit`       | `<div>`    | Both   | One source+gloss pair column. |
| `.gloss-src`        | `<span>`   | Both   | Transliteration inside a gloss unit. |
| `.gloss-tag`        | `<span>`   | Both   | Leipzig label inside a gloss unit. |
| `.gl`               | `<span>`   | Both   | A Leipzig abbreviation (2+ consecutive capitals); rendered in small caps. |
| `.toggle-bar`       | `<div>`    | Both   | Row of toggle switches (ezafe, translation, gloss) before each source-text block. |
| `.grammar-note-block` | `<div>` | Both   | Grammar note wrapper; light-blue background with left border. |
| `.grammar-note`     | `<h4>`     | Both   | Title heading inside a grammar note block. |
| `.ezafe`            | `<span>`   | Both   | Editorial kasra — from `"e": true` on JSON tokens, or `{e}` in prose strings. |

### Editing the stylesheet

`styles.css` lives at the project root so every chapter shares one visual identity. Adjust colors, font stacks, or sizes there once and every chapter re-renders with the new look — the HTML doesn't need to change. Print styling lives in `@media print` at the bottom of the file.

## Running the toolchain

```bash
# From the project root, for book directory study_guide/NN_book/:
python3 fetch_chapter.py <url> -o study_guide/NN_book/web.txt    # pull a chapter from the web
python3 build_site.py                                              # render all chapters + reference pages → _site/
python3 check_links.py                                             # verify all in-page anchor links resolve
```

`check_links.py` scans every HTML file in `_site/` and reports any `href="#..."` whose target `id="..."` does not exist in the same file. Run it after `build_site.py` to catch broken vocab links before pushing. Exits 0 if everything is clean, 1 if any broken links are found.

No dependencies beyond the Python 3.10+ standard library. CI runs `python3 build_site.py` and publishes `_site/` to GitHub Pages on every push to `main`/`master`; see `.github/workflows/pages.yml`.

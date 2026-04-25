# Persian Book of Mormon Study Guides

A reusable setup for producing learner-oriented English study guides from a Persian translation of the Book of Mormon. Each chapter lives in its own numbered directory (`01/`, `02/`, …) with a raw source, a cleaned source, and a markdown study guide.

```
.
├── README.md             # this file — conventions and workflow
├── normalize.py          # PDF-corruption normalizer
├── corruptions.json      # editable {corrupt: correct} word-pair lookup table
├── render.py             # Markdown → semantic HTML converter
├── styles.css            # shared stylesheet for all chapters' HTML
└── NN/                   # one directory per chapter (01, 02, …)
    ├── source.txt        # raw text pasted/extracted from the PDF
    ├── normalized.txt    # output of normalize.py
    ├── study_guide.md    # authored study guide (source of truth)
    └── study_guide.html  # rendered output; links to ../styles.css
```

## Per-chapter workflow

1. Extract the chapter's text from the PDF and save as `NN/source.txt`.
2. Run `python3 normalize.py NN/source.txt NN/normalized.txt`. Review the replacement summary printed to stderr.
3. Skim `NN/normalized.txt`. If any words still look wrong, determine the intended form, add the pair to `corruptions.json`, and re-run. (See "Source text corruption" below.)
4. Produce `NN/study_guide.md` from the normalized text following the conventions in "Study guide conventions."
5. Run `python3 render.py NN/study_guide.md NN/study_guide.html` to produce the HTML rendering. Open in a browser (or print to PDF) for a formatted reading copy.

## Source text corruption

The source PDF was extracted with a converter that mis-orders characters within certain ligature combinations. The corruption is systematic enough that a dictionary-based fix works. Patterns observed:

- `ر + letter` swaps with the following letter at word-start: `رشوع` ← `شروع`, `رسگذشت` ← `سرگذشت`, `مرصیان` ← `مصریان`, `بسرت-` ← `بستر-`.
- `م + letter` at the start of a word: `منی` ← `نمی`, `مناید` ← `نماید`, `منود` ← `نمود`, `متامی` ← `تمامی`.
- `Cام` where ا should be after the second consonant: `آسامن` ← `آسمان`, `هامن` ← `همان`, `بیشامری` ← `بیشماری`, `شام` ← `شما`, `ایامنشان` ← `ایمانشان`.
- `لا` ligature extracted as `ال` (positions swapped): `میالد` ← `میلاد`, `هالک` ← `هلاک`, `باال` ← `بالا`, `اعالم` ← `اعلام`, `خالصه` ← `خلاصه`, `واالی` ← `والای`. Note that real `ال` sequences (e.g. `دنبال`, `سال`, `حال`, `اورشلیم`) are unaffected — only words whose correct form contains `لا` are in the lookup.
- Missing ر in the translator's word for "the Lord": `سَور` ← `سرور` (Sarvar).
- Stray combining diacritics (fatha, damma, tashdid) occasionally appear at word boundaries or as standalone tokens. These are rendering noise — ignore them; don't treat an "extra" fatha in a word as a meaning clue.

Because some corrupt forms are legitimate substrings of other words (e.g. `رش` appears inside `اورشلیم`, `رس` inside `درست`, `مت` inside `رحمت`), replacements are applied as **whole-word substitutions** after stripping trailing punctuation, not as regex substring rewrites.

### Extending `corruptions.json`

It's a flat JSON object mapping `"corrupt_form": "correct_form"`. Add new entries as chapters reveal new glitches. Example:

```json
{
  "corrupt_form_here": "correct_form_here"
}
```

Keep the keys as the exact token you see (including attached combining marks if any). `normalize.py` strips trailing Persian and ASCII punctuation before lookup, so `مصریان،` and `مصریان` both match a `"مرصیان"` key.

## Study guide conventions

Each `NN/study_guide.md` has three top-level sections in this order: **Intro**, **Vocabulary**, **Grammar**.

### Intro (~½ page)

- One short paragraph summarizing the chapter's content.
- One short paragraph pointing at `NN/normalized.txt` so the reader can follow along.

### Transcription scheme (academic, with macrons)

| Persian sound | Transcription |
|---|---|
| Long vowels | `ā ī ū` |
| Short vowels | `a e o` |
| ش | `š` |
| ژ | `ž` |
| خ | `x` |
| ع | `ʿ` |
| ء / hamza | `ʾ` |
| چ | `č` |
| ج | `j` |
| Ezafe | `-e` after consonant, `-ye` after vowel |
| Object marker | `-rā` |
| Indefinite | `-ī` |
| Possessive suffixes | `-am -at -aš -mān -tān -šān` |

Long vowels always get macrons; short vowels never do. Write clitics with a hyphen. Capitalize proper nouns.

### Vocabulary section

- **Order of first appearance, grouped by verse**. A word appears once, in the verse where the reader first encounters it. Start with a `### Chapter summary (lines …)` subsection for the pre-verse-1 heading text, then `### Verse 1 (lines …)`, `### Verse 2 (lines …)`, … each with the new lemmas introduced in that verse. Cite line numbers from `NN/normalized.txt` in the subsection heading.
- **Lemmatize**: one entry per lemma (infinitive for verbs, singular citation form for nouns). Do **not** re-list a later inflected form (e.g. a new past-tense) as a fresh entry — forms are handled by the present-stem / past-participle notes on the original entry.
- **Scope**: every distinct lemma in the chapter, including function words.
- **Proper nouns**: mix inline where they first appear, tagged with `[proper]`.
- **Entry format**:

  ```
  **Persian** — *transcription* — English meaning [optional brief note]
  ```

  For verbs include the present stem:

  ```
  **نگاشتن** — *negāštan* (pres. *negār-*) — to write, inscribe [literary; = نوشتن]
  ```

  For function words include a short grammatical gloss:

  ```
  **را** — *-rā* — direct-object marker (post-nominal clitic)
  ```

- **Verb surface-form anchors**: the bare "(pres. *X-*)" notation is fine when the actual conjugated forms appearing in the chapter are transparently derivable from the lemma + present stem (e.g. `زادن` → past `زاد`, pp `زاده`). It is **not** fine when the surface form would surprise a learner. In those cases, explicitly anchor each surface form to its line number in `NN/normalized.txt`. The cases that always need anchors:

  1. **Suppletive present stems** — the pres stem shares no consonants with the infinitive's past stem. Examples: `دیدن` (pres. `bīn-` → *می بیند*), `آمدن` (pres. `ā-` → *می آید*, with epenthetic `-y-`), `دادن` (pres. `deh-` → *می دهد*), `رفتن` (pres. `rav-` → *رود*, where `rav-` + `-ad` collapses in spelling).
  2. **Conjugation quirks** — call out anything irregular about how `می-` / `بـ-` attach. The headline cases:
     - **داشتن** drops `می-` in the present indicative entirely — *دارد* / *دارند*, never `می‌دارد`.
     - **Prefixed compounds of داشتن** (`برداشتن`, `نگاه داشتن`, `بازداشتن`, …) reverse this: `می-` slots **between** the prefix and داشتن: *برمی دارد*, *برمی دارند*.
     - **Compound-verb subjunctives** routinely drop the `بـ-`: `توانا سازد` ≈ `توانا بسازد`, `هشدار دهد` ≈ `هشدار بدهد`.
     - **بودن** has multiple suppletive paradigms (*است*, *هست-*, *باش-*, *بود*); list the forms that actually appear.
  3. **Auxiliary uses** — when a verb shows up as a tense or voice helper rather than a content verb, list the auxiliary forms together. `خواستن` as future auxiliary (*خواهم نگاشت*, *نخواهی داشت*, …); `شدن` as passive auxiliary (*خوانده می شدند*, *برده خواهند شد*, …).
  4. **High-frequency verbs the reader will see in many forms** — for `بودن`, `شدن`, `کردن`, `داشتن`, `دادن`, summarize the paradigm visible in this chapter (3sg, 3pl, past, pp) rather than just the lemma.

  Anchor format inside the entry, in parens after the gloss: `(3sg pres. *surface translit*, as in \`phrase\` "English", line N; past *...* ...)`. Cite verbatim Persian from `NN/normalized.txt` and a line number — that's the contract that makes the anchor checkable.

  Verbs that don't need anchors (regular past stem matches infinitive, conjugation transparent, only past forms appear in the chapter): leave them in the bare lemma + present-stem format. Don't pad entries that don't need padding.

### Grammar section

10–12 tricky grammar points per chapter. For each point:

- A 1–3 sentence explanation.
- One example sentence **taken verbatim from the chapter's `normalized.txt`** — no invented examples.
- Three lines: Persian, transcription, English translation.

Standing list of points worth covering when they appear in a chapter:

- `چنین گذشت` — the "and it came to pass" calque
- Passive voice with `شدن` (past participle + شدن) — e.g. `آزار داده می‌شود`
- Future tense `خواه- + short infinitive` — e.g. `خواهند شد`, `نخواهم نگاشت`
- Subjunctive after `تا` — e.g. `تا آن را بخواند`
- Ezafe chains — e.g. `رحمت‌های مهرآمیز سرور`
- Indefinite marker `-ī` on nouns — e.g. `کتابی`, `ستونی`
- Direct-object marker `را` and its position after a noun phrase
- Compound verbs (noun/adjective + `کردن` / `شدن`)
- Possessive / pronominal suffixes `-am -at -aš -mān -tān -šān`
- Archaic / biblical register: `گفتا` narrative `-ā`, `آری`, `بنگرید`, the translator's `سرور` for "the Lord", bookish verbs like `نگاشتن`, `نیایش کردن`, `بانگ برآوردن`
- Relative clauses with `که`
- Imperfective `می-` and its negation `نمی-`

Don't force the full list into every chapter — only cover points the chapter actually contains.

## HTML rendering

`render.py` converts a chapter's Markdown study guide into semantic HTML and links it to `styles.css` at the project root. The goal is a readable on-screen reading copy that also prints to PDF cleanly, with Persian text set in a proper Persian font at a legible size and code/example blocks high-contrast.

```bash
python3 render.py NN/study_guide.md NN/study_guide.html
```

The HTML document structure is standard: `<main>` wraps the body; headings are `<h1>/<h2>/<h3>`; paragraphs are `<p>`; nested lists are rendered as properly-nested `<ul>/<li>`. The semantic elements unique to this project get classes from a small fixed taxonomy:

| Class | Applied to | Where it comes from in Markdown |
|---|---|---|
| `.vocab` | `<ul>` | Any bullet list whose items all begin with `**bold**` (treated as a vocab list). |
| `.vocab-entry` | `<li>` | Each item inside a `.vocab` list. |
| `.persian` | `<strong>` / inline | The bolded Persian headword at the start of a vocab entry. Also applied to Persian-containing spans elsewhere via the stylesheet's font fallback on `<code>`. |
| `.translit` | `<em>` | The first italic span in a vocab entry (the transliteration after the headword). |
| `.proper` | `<span>` | The literal text `[proper]` inside a vocab entry (tag for proper nouns). |
| `.example` | `<div>` | Replaces `<blockquote>`. Any Markdown blockquote is treated as a three-line grammar example. |
| `.example-fa` | `<div>` | First line of an example — Persian + (optional) line-ref prefix. |
| `.example-tr` | `<div>` | Second line of an example — italic transliteration. |
| `.example-en` | `<div>` | Third line of an example — English translation. |
| `.line-ref` | `<span>` | The `Lines N–M:` prefix at the start of `.example-fa`. |

The parser is deliberately narrow: it handles headings, paragraphs, bold/italic/inline-code, nested `- ` bullet lists, and `> ` blockquotes. It does not handle tables, code fences, or links. If a future chapter needs richer Markdown, swap in [python-markdown](https://pypi.org/project/Markdown/) or [markdown-it-py](https://pypi.org/project/markdown-it-py/) (add a `requirements.txt` and a venv) and keep the post-processing step that injects the classes above.

### Editing the stylesheet

`styles.css` lives at the project root so every chapter shares one visual identity. Adjust colors, font stacks, or sizes there once and every chapter re-renders with the new look — the HTML doesn't need to change. Print styling lives in `@media print` at the bottom of the file.

## Running the toolchain

```bash
# From the project root, for chapter NN:
python3 normalize.py NN/source.txt NN/normalized.txt   # clean PDF corruption
python3 render.py NN/study_guide.md NN/study_guide.html  # Markdown → HTML
```

No dependencies beyond the Python 3.10+ standard library.

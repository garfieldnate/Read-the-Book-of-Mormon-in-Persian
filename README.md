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

- **Order of first appearance, grouped by verse, sub-grouped by source line**. A word appears once, in the verse where the reader first encounters it. Use:
  - `### Verse N (lines X–Y)` (h3) — one per verse / per heading section. Renders with a prominent solid top rule.
  - `#### Line N` (h4) — within each section, sub-divide into per-source-line groups. Renders as a small uppercase chip with a dashed rule above. Skip lines that introduce no new lemmas (don't emit an empty `Line 22` block — go straight from `Line 21` to `Line 23`).
  - Source line numbers refer to `NN/normalized.txt`. Skip page-header artifact lines (`۱یافین …`).
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

- **Metadata sub-bullets** (the `*Etym*`, `*Forms*`, and `*Family*` lines under a vocab entry). Keep the headline of an entry **clean** — just `**Persian** — *translit* — meaning [maybe a one-word register tag like "literary"]`. Anything more goes in nested bullets directly underneath:

  ```markdown
  - **شادمانی** — *šādmānī* — joy, gladness
    - *Etym*: شاد *šād* + -مان *-mān* (adjectival) + -ی *-ī* (abstract).
    - *Family*: شاد *šād* "happy"; شادمان *šādmān* "joyful, cheerful".
    - *Forms*: collocation `شادمانی کردن` "to rejoice".
  ```

  Each italic label (`*Etym*`, `*Forms*`, `*Family*`) at the start of a sub-bullet is recognized by `render.py` and rendered as a small chip-style tag in HTML. All labels are optional — include each one only if it actually has content. Indent sub-bullets with **two spaces**.

- **When to add `*Etym*`** (etymology / morpheme breakdown — included only when the answer is interesting):

  - **Arabic loanwords** — common in religious/literary register. Note the source language and, when easy to identify, the triliteral root. Example: `*Etym*: from Arabic, root r-ḥ-m "compassion"`.
  - **Compounds with meaningful morphemes** — break down the parts. Example: `*Etym*: سر *sar* "head" + گذشت *gozašt* "past" (← گذشتن "to pass"); literally "what passed at one's head"`.
  - **Proper nouns of foreign origin** — Hebrew (most BoM names via Arabic / English transliteration), or English (BoM-coined). Example: `*Etym*: Hebrew יהודה *Yəhūdā* "praised", via Arabic`.
  - **Native, non-compound Persian words** — *do not* add `*Etym*`. Don't write "native Persian"; absence is the signal.

- **When to add `*Family*`** (related words to memorize alongside this entry — different from `*Etym*`, which is the linguistic breakdown):

  - When the entry's stem is **a useful Persian word in its own right** that doesn't otherwise appear in the chapter. Example: `شادمانی` is in the chapter, but seeing `شاد` "happy" and `شادمان` "joyful" listed alongside lets the reader pick up three vocabulary items for the price of one.
  - When the entry has **derivational siblings** the reader will meet later (e.g., `شورش` "rebellion" → list شور "fervor" and شوریدن "to revolt"; `ستایش` "praise" → list the source verb ستودن).
  - For **compounds** whose components are themselves vocabulary worth memorizing (e.g., `سرگذشت` → سر "head" + گذشتن "to pass"; both are headwords elsewhere in this chapter, but the Family note re-lists them with brief glosses for quick reference).

  Format: short list with each related form's translit and a one-or-two-word gloss, separated by `;`. Example: `*Family*: شاد *šād* "happy"; شادمان *šādmān* "joyful"`. Don't repeat the entry's headword; don't repeat detail already in `*Etym*`.

- **When to add `*Forms*`** (morphology, conjugation, common collocations):

  1. **Verbs whose surface forms in the chapter would surprise a learner**. Always include `*Forms*` for:
     - **Suppletive present stems** (no shared consonants with infinitive): `دیدن` (pres. `bīn-` → *می بیند*), `آمدن` (pres. `ā-` → *می آید*, with epenthetic `-y-`), `دادن` (pres. `deh-` → *می دهد*), `رفتن` (pres. `rav-` → *رود*, where `rav-` + `-ad` collapses in spelling).
     - **Conjugation quirks**: `داشتن` drops `می-` in the present indicative (*دارد* / *دارند*, never `می‌دارد`). Prefixed compounds of داشتن reverse this: `می-` slots **between** the prefix and داشتن (*برمی دارد*). Compound-verb subjunctives routinely drop the `بـ-` (`توانا سازد` ≈ `توانا بسازد`).
     - **Auxiliary uses**: `خواستن` as future auxiliary (*خواهم نگاشت*, …); `شدن` as passive auxiliary (*خوانده می شدند*, …).
     - **High-frequency verbs that show up in many shapes** (`بودن`, `شدن`, `کردن`, `داشتن`, `دادن`): summarize the paradigm visible in this chapter (3sg, 3pl, past, pp).
  2. **Common collocations or related compound forms** of any lemma — what would have been an inline parenthetical (e.g., on `دنبال`, the pair `به دنبال` / `بدنبال`; on `خشم`, the verb `خشم گرفتن`). Move these to `*Forms*:` instead of the headline.
  3. **Regular verbs** whose past stem matches the infinitive transparently (`زادن` → `زاد`/`زاده`, `شنیدن` → `شنید`/`شنیده`, etc.) — *do not* add `*Forms*`. The bare `(pres. *stem-*)` annotation in the headline is enough.

  Inside `*Forms*`, cite **verbatim Persian from `NN/normalized.txt` plus a line number** so the anchor is checkable. Format: `*Forms*: 3sg pres. *surface translit*, as in \`phrase\` "English", line N; past *…*; pp. *…*.`

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
| `.vocab-meta` | `<ul>` | Sub-list directly inside a `.vocab-entry` (the `Etym` / `Forms` block). |
| `.vocab-etym` | `<li>` | Item in `.vocab-meta` whose label is `*Etym*` or `*Etymology*`. |
| `.vocab-forms` | `<li>` | Item in `.vocab-meta` whose label is `*Forms*` or `*Form*`. |
| `.vocab-family` | `<li>` | Item in `.vocab-meta` whose label is `*Family*` or `*Kin*`. |
| `.vocab-meta-other` | `<li>` | Fallback class on a `.vocab-meta` item with an unrecognized leading label. |
| `.meta-label` | `<span>` | The `Etym` / `Forms` chip at the start of a meta sub-bullet (rendered as a small uppercase tag). |
| `.persian` | `<strong>` | The bolded Persian headword at the start of a vocab entry. |
| `.translit` | `<em>` | The first italic span in a vocab entry (the transliteration after the headword). |
| `.proper` | `<span>` | The literal text `[proper]` inside a vocab entry (tag for proper nouns). |
| `.example` | `<div>` | Replaces `<blockquote>`. Any Markdown blockquote is treated as a three-line grammar example. |
| `.example-fa` | `<div>` | First line of an example — Persian + (optional) line-ref prefix. |
| `.example-tr` | `<div>` | Second line of an example — italic transliteration. |
| `.example-en` | `<div>` | Third line of an example — English translation. |
| `.line-ref` | `<span>` | The `Lines N–M:` prefix at the start of `.example-fa`. |
| `<h3>` | (element) | Section heading (`### Verse 1 (lines 25–33)`); styled with a solid top border to mark section boundaries. |
| `<h4>` | (element) | Source-line marker (`#### Line 25`); styled small/uppercase with a dashed top rule for in-section line groups. |

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

# Persian Book of Mormon Study Guides

A reusable setup for producing learner-oriented English study guides from a Persian translation of the Book of Mormon. Each chapter lives in a per-book directory (`01_nephi/`, `02_nephi/`, …) with a raw source, a cleaned source, and one or more markdown study guides — `chN.md` per chapter of the book.

```
.
├── README.md                 # this file — conventions and workflow
├── normalize.py              # PDF-corruption normalizer
├── corruptions.json          # editable {corrupt: correct} word-pair lookup table
├── fetch_chapter.py          # download a chapter's clean text from churchofjesuschrist.org
├── render.py                 # Markdown → semantic HTML converter
├── build_site.py             # walks every NN_*/chN.md and builds _site/
├── styles.css                # shared stylesheet for all chapters' HTML
├── .github/workflows/
│   └── pages.yml             # CI: runs build_site.py and deploys to GitHub Pages
└── NN_book/                  # one directory per book (01_nephi, 02_nephi, 03_jacob, …)
    ├── source.txt            # raw text pasted/extracted from the PDF
    ├── normalized.txt        # output of normalize.py
    ├── ch1.md                # study guide for chapter 1 (source of truth)
    ├── ch2.md                # study guide for chapter 2 (etc.)
    └── …
```

The directory prefix is the **book index** (01–15 in publication order: 1 Nephi, 2 Nephi, Jacob, Enos, …); the slug after the underscore is the book's English name (lowercased, words separated with `_`). The first H1 of each `chN.md` is the canonical display title (e.g. `# 1 Nephi 1 — Persian Study Guide`); `build_site.py` reads it for the index page.

Rendered HTML is **not committed**. `build_site.py` produces `_site/` containing one HTML page per chapter plus `index.html` and `styles.css`; GitHub Actions runs the build on every push to `main`/`master` and publishes `_site/` to GitHub Pages. To preview locally:

```bash
python3 build_site.py
open _site/index.html        # or: python3 -m http.server -d _site
```

## Per-chapter workflow

There are two ways to acquire a chapter's source text:

- **Web (preferred for new chapters)** — `python3 fetch_chapter.py <url>` downloads
  the chapter from `churchofjesuschrist.org` (Persian edition) and prints
  structured plain text grouped by element class: `# title`, `# subtitle`,
  `# intro` (book-level summary, only on chapter 1 of each book),
  `# chapter`, `# study-summary` (chapter heading paragraph), `# verse 1`
  … `# verse N`. Pipe with `-o NN_book/web.txt` to save. The web edition
  is already clean; no normalisation step needed.
- **PDF (legacy)** — copy the chapter's text out of `book-of-mormon-59010-pes.pdf`
  into `NN_book/source.txt`, then run `python3 normalize.py NN_book/source.txt
  NN_book/normalized.txt` to apply the dictionary-based corruption fixes.
  Skim the result; if any words still look wrong, add a pair to
  `corruptions.json` and re-run (see "Source text corruption" below).

For chapter 1 of 1 Nephi, the chapter body in `01_nephi/normalized.txt`
came from the PDF; the **book summary** in `01_nephi/ch1.md` was later
re-sourced from the web edition (since the PDF wraps the summary across
column boundaries that split words mid-token). New chapters should prefer
the web fetcher for everything.

Once the source text is in hand:

1. Produce `NN_book/chN.md` from the source text, following the conventions
   in "Study guide conventions" below.
2. Run `python3 build_site.py` to render every chapter into `_site/`. Open
   `_site/index.html` in a browser to read the formatted output. (For a
   single-file render outside the site: `python3 render.py NN_book/chN.md
   /tmp/preview.html`.)

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
| Diphthongs | `ow` `ay` `ey` |
| ش | `š` |
| ژ | `ž` |
| خ | `x` |
| چ | `č` |
| ج | `j` |
| ع | `ʿ` |
| ء / hamza | `ʾ` |
| ق | `q` |
| Arabic emphatics | `ṣ ẓ ḥ ṭ` (see below) |
| Ezafe | `-e` after consonant, `-ye` after vowel |
| Object marker | `-rā` |
| Indefinite | `-ī` |
| Possessive suffixes | `-am -at -aš -mān -tān -šān` |

Long vowels always get macrons; short vowels never do. Write clitics with a hyphen. Capitalize proper nouns.

**Dotted-below consonants** (`ṣ ẓ ḥ ṭ`) are how academic transliteration spells the Arabic emphatic letters borrowed into Persian. The dot preserves the spelling distinction (so you can recognize that the word is an Arabic loan written with the dotted letter), but in modern Persian pronunciation each one collapses onto its non-emphatic counterpart:

- `ṣ` (ص) is pronounced like `s` (س) — e.g. *ṣaxre* "rock", *Ṣedqiyā* "Zedekiah".
- `ẓ` (ظ; also ض) is pronounced like `z` (ز) — e.g. *ʿaẓīm* "great".
- `ḥ` (ح) is pronounced like `h` (ه) — e.g. *ḥattā* "even", *rūḥ* "spirit".
- `ṭ` (ط) is pronounced like `t` (ت) — e.g. *loṭf* "grace", *moṭlaq* "absolute".

Two further conventions:

- `q` (ق) is uvular in classical/Arabic. Iranian Persian usually merges it with غ as a voiced uvular [ɢ] / [ɣ]; transliteration keeps the `q` spelling regardless. E.g. *qodrat* "power", *qāder* "able".
- `ʿ` (ع, *ʿayn*) is an Arabic pharyngeal in the source. In Persian it usually surfaces as a glottal stop / syllable break, often silent. E.g. *ʿaẓīm*, *šorūʿ*.

**Diphthongs** — all *falling* (vowel + glide), never rising:

- `ow` — `o` followed by a final `w`-glide. Closest English match: "mow", "row", "stowed". So `مورد` *mowred* "case" rhymes with English "stowed", **not** with "mouth"; cf. *mowʿūd* "promised", *towbe* "repentance", *partow* "ray", *dowre* "period".
- `ay` — `a` followed by a final `y`-glide. Closest English match: "eye", "high". E.g. `علیه` *ʿalayhi* "against".
- `ey` — `e` followed by a final `y`-glide. Closest English match: "say", "hey". E.g. `پی` *pey* "track".

### Vocabulary section

- **Each section opens with the source text, immediately followed by the vocab for that section.** The chapter is divided into a **book summary** (the header for the whole book of Nephi/Mosiah/etc., before chapter 1), a **chapter summary** (the per-chapter subheading), and the numbered **verses**:
  - **Book summary** — sentence-by-sentence, sourced from the publisher's clean web edition (use `python3 fetch_chapter.py <url>` to pull a chapter, see "Per-chapter workflow"). Open with a `#### Title` block carrying the book name and a `#### Subtitle` block carrying the short reign-statement, then one `#### Sentence N` (h4) heading per sentence in the book-level summary paragraph, splitting on `.`. Each sub-block carries one backtick'd Persian sentence followed by the vocab it introduces. Sub-block numbering does **not** correspond to line numbers in `normalized.txt` — the book summary is a single paragraph on the web edition, and the PDF's typographic line wraps split words mid-token (e.g. `ثریّا`, `خرّمساران`), so we don't honor them. If a sentence introduces no new lemmas, emit the heading and the backtick'd Persian followed by an italic `*(No new lemmas — every word in this sentence has already been introduced.)*` note in place of a vocab list.
  - **Chapter summary** — `### Chapter summary (lines X–Y)` (h3) followed by the entire summary text on a single line wrapped in backticks (no internal line breaks), then a single flat vocab list for the whole summary.
  - **Each verse** — `### Verse N (lines X–Y)` (h3) followed by the entire verse text on a single line wrapped in backticks, then a single flat vocab list for that verse. **Do not** sub-divide a verse with `#### Line N` headings; the source-line anchors live inside `*Forms*` citations on individual entries instead.
  - Source line numbers refer to `NN_book/normalized.txt`. Skip page-header artifact lines (e.g. `۱یافین …`) when transcribing the text inline; cite the surrounding line numbers in the `(lines X–Y)` heading.
  - When the source PDF's column flow split a token across lines (e.g. `حت` + `ّی` = `حتّی`), reassemble it in the inline text — the displayed Persian should read continuously.
- **Order of first appearance**. A word appears once, in the verse where the reader first encounters it.
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
    - *Etym*: `شاد` + `-مان` (adjectival) + `-ی` (abstract).
    - *Family*: `شاد` *šād* "happy"; `شادمان` *šādmān* "joyful, cheerful".
    - *Forms*: collocation `شادمانی کردن` "to rejoice".
  ```

  Each italic label (`*Etym*`, `*Forms*`, `*Family*`) at the start of a sub-bullet is recognized by `render.py` and rendered as a small chip-style tag in HTML. All labels are optional — include each one only if it actually has content. Indent sub-bullets with **two spaces**.

  **Inline Persian in meta sub-bullets always uses backticks.** Every Persian word or morpheme fragment (including prefix/suffix notation like `` `-ی` `` and `` `نا-` ``) must be wrapped in backtick code spans. This applies to all three label types equally — `*Forms*` was already consistent; `*Etym*` and `*Family*` must follow the same rule. The backtick styling gives Persian text a legible size and a distinct background that makes it easy to pick out from the surrounding Latin transcription and English gloss. The headword in the vocab entry headline (`**Persian**`) is exempt — it gets its own larger `.persian` styling instead.

- **When to add `*Etym*`** (etymology / morpheme breakdown — included only when the answer is interesting):

  - **Arabic loanwords** — common in religious/literary register. Note the source language and, when easy to identify, the triliteral root. Example: `*Etym*: from Arabic, root r-ḥ-m "compassion"`.
  - **Compounds with meaningful morphemes** — break down the parts. Example: ``*Etym*: `سر` *sar* "head" + `گذشت` *gozašt* "past" (← `گذشتن` "to pass"); literally "what passed at one's head".``
  - **Proper nouns of foreign origin** — Hebrew (most BoM names via Arabic / English transliteration), or English (BoM-coined). Example: `*Etym*: Hebrew יהודה *Yəhūdā* "praised", via Arabic`.
  - **Native, non-compound Persian words** — *do not* add `*Etym*`. Don't write "native Persian"; absence is the signal.

- **When to add `*Family*`** (related words to memorize alongside this entry — different from `*Etym*`, which is the linguistic breakdown):

  - When the entry's stem is **a useful Persian word in its own right** that doesn't otherwise appear in the chapter. Example: `شادمانی` is in the chapter, but seeing `شاد` "happy" and `شادمان` "joyful" listed alongside lets the reader pick up three vocabulary items for the price of one.
  - When the entry has **derivational siblings** the reader will meet later (e.g., `شورش` "rebellion" → list `شور` "fervor" and `شوریدن` "to revolt"; `ستایش` "praise" → list the source verb `ستودن`).
  - For **compounds** whose components are themselves vocabulary worth memorizing (e.g., `سرگذشت` → `سر` "head" + `گذشتن` "to pass"; both are headwords elsewhere in this chapter, but the Family note re-lists them with brief glosses for quick reference).

  Format: short list with each related form's translit and a one-or-two-word gloss, separated by `;`. Example: ``*Family*: `شاد` *šād* "happy"; `شادمان` *šādmān* "joyful".`` Don't repeat the entry's headword; don't repeat detail already in `*Etym*`.

- **When to add `*Forms*`** (morphology, conjugation, common collocations):

  1. **Verbs whose surface forms in the chapter would surprise a learner**. Always include `*Forms*` for:
     - **Suppletive present stems** (no shared consonants with infinitive): `دیدن` (pres. `bīn-` → *می بیند*), `آمدن` (pres. `ā-` → *می آید*, with epenthetic `-y-`), `دادن` (pres. `deh-` → *می دهد*), `رفتن` (pres. `rav-` → *رود*, where `rav-` + `-ad` collapses in spelling).
     - **Conjugation quirks**: `داشتن` drops `می-` in the present indicative (*دارد* / *دارند*, never `می‌دارد`). Prefixed compounds of داشتن reverse this: `می-` slots **between** the prefix and داشتن (*برمی دارد*). Compound-verb subjunctives routinely drop the `بـ-` (`توانا سازد` ≈ `توانا بسازد`).
     - **Auxiliary uses**: `خواستن` as future auxiliary (*خواهم نگاشت*, …); `شدن` as passive auxiliary (*خوانده می شدند*, …).
     - **High-frequency verbs that show up in many shapes** (`بودن`, `شدن`, `کردن`, `داشتن`, `دادن`): summarize the paradigm visible in this chapter (3sg, 3pl, past, pp).
  2. **Common collocations or related compound forms** of any lemma — what would have been an inline parenthetical (e.g., on `دنبال`, the pair `به دنبال` / `بدنبال`; on `خشم`, the verb `خشم گرفتن`). Move these to `*Forms*:` instead of the headline.
  3. **Regular verbs** whose past stem matches the infinitive transparently (`زادن` → `زاد`/`زاده`, `شنیدن` → `شنید`/`شنیده`, etc.) — *do not* add `*Forms*`. The bare `(pres. *stem-*)` annotation in the headline is enough.

  Inside `*Forms*`, cite **verbatim Persian from `NN_book/normalized.txt` plus a line number** so the anchor is checkable. Format: `*Forms*: 3sg pres. *surface translit*, as in \`phrase\` "English", line N; past *…*; pp. *…*.`

- **Irregular reading warnings (⚠️)**: flag Arabic loanwords whose Persian spelling would mislead a learner into a wrong pronunciation. Place the ⚠️ sub-bullet **first** under the headword, before any `*Etym*` line — and only on the sub-bullet, never on the headword line itself:

  ```markdown
  - **حتّی** — *ḥattā* — even
    - ⚠️ _Alif maqṣūra_: the final `ی` represents Arabic _alif maqṣūra_ (`الألف المقصورة`) — a long -ā vowel written `ى` at the end of certain Arabic words. Learners may accidentally read it as _\*ḥattī_.
    - *Etym*: from Arabic *ḥattā*, originally a preposition "until, up to".
  ```

  Rules:
  - One ⚠️ only — on the sub-bullet. No ⚠️ on the headword line.
  - The italic label names the specific phenomenon. Keep the explanation to one sentence; end with `Learners may accidentally read it as _\*wrongform_.` (the `\*` is the standard linguistic convention for an incorrect form; it renders as a literal asterisk in HTML).
  - Persian in backticks; transcriptions in italic underscores.
  - In HTML, render.py assigns these bullets `.vocab-meta-other` (the ⚠️ precedes any italic label, so the label-detection regex does not match).

  Common categories:

  | Label | When to use |
  |---|---|
  | `_Alif maqṣūra_` | Arabic final ى — written ی in Persian — is read -ā, not -ī (e.g. `حتّی` *ḥattā* "even"). |
  | `_Diphthong -ay- written as ی_` | Arabic *-ay-* diphthong where learners expect Persian long *-ī-* (e.g. `علیه` *ʿalayhi* "against"). |

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

`render.py` converts a chapter's Markdown study guide into semantic HTML and links it to `styles.css`. The goal is a readable on-screen reading copy that also prints to PDF cleanly, with Persian text set in a proper Persian font at a legible size and code/example blocks high-contrast. `build_site.py` invokes `render()` for every `NN_book/chN.md` it finds, drops the result under `_site/NN_book/chN.html`, and emits a top-level `_site/index.html` that lists all chapters and gives the source publication's original title and copyright.

```bash
python3 build_site.py                     # full site → _site/
python3 render.py NN_book/chN.md /tmp/x.html  # one-off single-file render
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
| `<h4>` | (element) | Sentence / line marker (`#### Sentence 3`, `#### Title`); styled small/uppercase with a dashed top rule for sub-blocks under a section. |

The parser is deliberately narrow: it handles headings, paragraphs, bold/italic/inline-code, nested `- ` bullet lists, and `> ` blockquotes. It does not handle tables, code fences, or links. If a future chapter needs richer Markdown, swap in [python-markdown](https://pypi.org/project/Markdown/) or [markdown-it-py](https://pypi.org/project/markdown-it-py/) (add a `requirements.txt` and a venv) and keep the post-processing step that injects the classes above.

### Editing the stylesheet

`styles.css` lives at the project root so every chapter shares one visual identity. Adjust colors, font stacks, or sizes there once and every chapter re-renders with the new look — the HTML doesn't need to change. Print styling lives in `@media print` at the bottom of the file.

## Running the toolchain

```bash
# From the project root, for book directory NN_book/:
python3 fetch_chapter.py <url> -o NN_book/web.txt                # pull a chapter cleanly from the web (preferred)
python3 normalize.py NN_book/source.txt NN_book/normalized.txt   # legacy: clean PDF-extraction corruption
python3 build_site.py                                              # render every chN.md → _site/
```

No dependencies beyond the Python 3.10+ standard library. CI runs `python3 build_site.py` and publishes `_site/` to GitHub Pages on every push to `main`/`master`; see `.github/workflows/pages.yml`.

# Persian Book of Mormon Study Guides

Just want to study? View the study guide [here](https://nateglenn.com/Read-the-Book-of-Mormon-in-Persian/).

> This project is largely LLM-generated for my own study purposes. The README is mostly intended as instructions to an LLM for generating further study guides for the next chapters.

> I am just learning Persian myself, so if you see any errors or have suggestions for improvement, please open an issue or submit a PR!

A reusable setup for producing learner-oriented English study guides from a Persian translation of the Book of Mormon. Each chapter lives in `study_guide/NN_book/` — one directory per book. **The authoritative format for chapter content is a pair of JSON files** (`chN.source.json` + `chN.study.json`); the legacy `chN.md` files are kept as human-readable archives but are not rendered. New chapters should be generated as JSON by an LLM following the schemas in "Chapter JSON format" below.

```
.
├── README.md                   # this file — conventions and workflow
├── fetch_chapter.py            # download a chapter's clean text from churchofjesuschrist.org
├── render.py                   # Markdown → semantic HTML (used for reference pages only)
├── render_json.py              # JSON → semantic HTML (used for chapter pages)
├── build_site.py               # walks study_guide/NN_*/chN.{source,study}.json and builds _site/
├── migrate_md_to_json.py       # one-time migration tool: chN.md → chN.source.json + chN.study.json
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
        ├── ch1.md              # archived Markdown (not rendered)
        └── …
```

The directory prefix is the **book index** (01–15 in publication order: 1 Nephi, 2 Nephi, Jacob, Enos, …); the slug after the underscore is the book's English name (lowercased, words separated with `_`). `build_site.py` reads the title from the first H1 of `ch1.study.json`'s `intro` field (or falls back to `book + chapter`). It also renders the standalone Markdown reference pages linked from the index.

Rendered HTML is **not committed**. `build_site.py` produces `_site/` containing one HTML page per chapter plus `index.html` and `styles.css`; GitHub Actions runs the build on every push to `main`/`master` and publishes `_site/` to GitHub Pages. To preview locally:

```bash
python3 build_site.py
open _site/index.html        # or: python3 -m http.server -d _site
```

## Per-chapter workflow

Use `python3 fetch_chapter.py <url>` to download a chapter from `churchofjesuschrist.org` (Persian edition). It prints structured plain text grouped by element class: `# title`, `# subtitle`, `# intro` (book-level summary, only on chapter 1 of each book), `# chapter`, `# study-summary` (chapter heading paragraph), `# verse 1` … `# verse N`. Pipe with `-o study_guide/NN_book/webN.txt` to save.

Once the source text is in hand, generate the two JSON files using an LLM (feed it this README plus the `webN.txt` fetch output):

1. Produce `study_guide/NN_book/chN.source.json` — the tokenized scripture text with interlinear gloss and English translation, following the **`chN.source.json` schema** below.
2. Produce `study_guide/NN_book/chN.study.json` — the intro, vocabulary entries, and grammar notes, following the **`chN.study.json` schema** below.
3. Run `python3 build_site.py` to render every chapter into `_site/`. Open
   `_site/index.html` in a browser to read the formatted output.
4. Run `python3 check_links.py` to verify all in-page anchor links resolve. Fix any broken links before pushing.

## Chapter JSON format

Each chapter is stored as two JSON files in `study_guide/NN_book/`:

### `chN.source.json`

Holds the tokenized scripture text. Generate one section per structural element of the chapter.

```jsonc
{
  "book": "1 Nephi",      // display name
  "chapter": 1,           // integer
  "sections": [
    // section "type" values:
    //   "book-summary-title"     — book title heading (chapter 1 of a book only)
    //   "book-summary-subtitle"  — book subtitle heading (chapter 1 of a book only)
    //   "book-summary-sentence"  — one sentence from the book-level summary paragraph;
    //                              has a "number" field (1, 2, 3, …)
    //   "chapter-summary"        — the per-chapter subheading paragraph
    //   "verse"                  — a numbered verse; has a "number" field

    {
      "type": "verse",
      "number": 1,

      // Pre-tokenized Persian text. Each element is one of:
      //   {"fa": "word"}                    — Persian token; linked via vocab map
      //   {"fa": "word", "lemma": "base"}   — explicit lemma for vocab map lookup
      //   {"fa": "word", "e": true}         — editorial ezafe follows this token
      //   {"p": "،"}                        — punctuation (no vocab link, no space before)
      // Spaces between adjacent "fa" tokens are implicit.
      // Each "fa" token may also carry a "gloss" sub-object (see below).
      "tokens": [
        {"fa": "من", "gloss": {"src": "man", "gloss": "1SG"}},
        {"fa": "نیفای", "gloss": {"src": "Nīfāy", "gloss": "Nephi"}},
        {"p": "،"},
        {"fa": "از", "gloss": {"src": "az", "gloss": "from"}},
        {"fa": "پدر",
         "e": true,
         "gloss": {"src": "pedar=e", "gloss": "father=EZ"}},
        {"fa": "مادر",
         "e": true,
         "gloss": {"src": "mādar=e", "gloss": "mother=EZ"}},
        {"fa": "خوبی", "gloss": {"src": "xūb-ī", "gloss": "good-INDEF"}},
        {"fa": "زاده", "gloss": {"src": "zāde", "gloss": "bear-PTCP.PST"}},
        {"fa": "شده", "gloss": {"src": "šode", "gloss": "become-PTCP.PST"}},
        {"p": "."}
      ],

      "en": "I, Nephi, having been born of goodly parents…"
    }
  ]
}
```

**`gloss` sub-object** on each `fa` token (Leipzig interlinear data):
- `src` — romanized transliteration of the token with morphological boundaries (`-` for bound morphemes, `=` for clitics).
- `gloss` — Leipzig gloss label (lexical content lowercase, grammatical abbreviations UPPERCASE, multi-part joined with `.`).
- Tokens missing a `gloss` sub-object render without a gloss column entry (marks a known gap).
- `می` and `نمی` are kept as separate tokens in the `tokens` array (since the publisher writes them with a space), and each gets its own `gloss` sub-object (e.g. `{"src": "mī", "gloss": "IMPF"}`). In the vocab map, however, `می`/`نمی` are **not** given their own headword entries — they are treated as part of the following verb (see below).

---

### `chN.study.json`

Holds the annotation. Sections must align with the source JSON by `section_type` + `number`.

```jsonc
{
  "book": "1 Nephi",
  "chapter": 1,
  "intro": "Opening paragraph summarizing the chapter…\n\nSecond paragraph if needed.",

  "sections": [
    {
      "section_type": "verse",  // matches source JSON "type"
      "number": 1,              // present on "book-summary-sentence" and "verse" types
      "entries": [
        // --- headword entry ---
        {
          "type": "headword",
          "id": "نگه_داشتن",    // stable ID used as anchor; defaults to persian with spaces→_
          "persian": "نگه داشتن",
          "translit": "negah dāštan",
          "meaning": "to keep, maintain; to hold",
          "tags": [],           // [] | ["proper"] | ["bound-morpheme"]
          "pres_stem": {        // null for non-verbs
            "fa": "نگه دار",
            "translit": "negah dār-"
          },
          "warning": null,      // markdown string for ⚠️ note, or null
          // etym is null or an object:
          //   {"prose": "markdown string"}                         — non-Arabic
          //   {"prose": "markdown string", "arabic_form": "..."}  — Arabic borrowing
          // arabic_form is a controlled value from the list below; the renderer
          // appends a colored tag linking to the matching section on arabic.html.
          // Allowed arabic_form values:
          //   Verbal nouns:  "Form I verbal noun" … "Form X verbal noun"
          //   Active parts:  "Form I active participle" / "Form II active participle" /
          //                  "Form III active participle" / "Form IV active participle" /
          //                  "Form X active participle"
          //   Passive parts: "Form I passive participle" / "Form II passive participle" /
          //                  "Form IV passive participle"
          //   Other:         "nominal pattern"  "elative (Form IV)"
          "etym": null,
          "family": null,
          // "forms" is an ordered array. Each element is one of:
          //   {"fa": "surface", "translit": "...", "desc": "..."}
          //     — a registerable surface form; "fa" is the vocab-map lookup key;
          //       "translit" and "desc" are optional
          //   {"note": "..."}
          //     — free prose note (no vocab-map registration)
          "forms": [
            {
              "fa": "نگه دارند",
              "translit": "negah dār-and",
              "desc": "3pl sbjv."
            },
            {
              "fa": "نگه داشت",
              "translit": "negah dāšt",
              "desc": "past 3sg"
            }
          ]
        },

        // --- variant entry (archaic/surface form, not a citation-form lemma) ---
        {
          "type": "variant",
          "persian": "گفتا",
          "translit": "goftā",
          "meaning": "archaic narrative past of `گفتن`; see [Grammar: Narrative -ā](#grammar-narrative-a)"
        },

        // --- grammar note ---
        {
          "type": "grammar-note",
          "title": "Grammar: `ای کاش` + imperfect — wishing construction",
          "body": "`ای کاش` introduces an unfulfilled wish. The verb takes the **past imperfect**.",
          "examples": [
            {
              "ref": "Verse 9",
              "ref_anchor": "verse-9",
              "persian": "ای کاش تو هم می توانستی",
              "translit": "ey kāš to ham mī-tavānestī",
              "en": "O that thou mightest…"
            }
          ],
          "closing": "Optional prose after the last example."
        },

        // --- no new lemmas marker ---
        {
          "type": "no-new-lemmas"
        }
      ]
    }
  ]
}
```

**`می`/`نمی` convention**: do **not** create a headword entry for `می` or `نمی`. The imperfective prefix is treated as part of the verb it modifies. In source text rendering, when a `می`/`نمی` token is followed by a verb token that has a vocab entry, both are wrapped in a single `<a>` link to the verb's anchor. In `forms` entries, write `می` and the verb stem together in one backtick group: `` `می بیند` `` (not `` `می` `بیند` ``).

---

## Study guide conventions

Each `study_guide/NN_book/chN.md` has three top-level sections in this order: **Intro**, **Vocabulary**, **Grammar**.

### Intro (~½ page)

One short paragraph summarizing the chapter's content.

### Transcription scheme

The full transliteration table, pronunciation notes, and diphthong guide live in `study_guide/transcription.md` (rendered as a standalone reference page at `_site/study_guide/transcription.html`). Refer to that file for the authoritative scheme; do not duplicate it here.

### Vocabulary section

- **Each section opens with the source text, followed by an interlinear gloss, an English translation, and then the vocab for that section** (in that order). The chapter is divided into a **book summary** (the header for the whole book of Nephi/Mosiah/etc., before chapter 1), a **chapter summary** (the per-chapter subheading), and the numbered **verses**:
  - **Book summary** — sentence-by-sentence, sourced from the publisher's clean web edition (use `python3 fetch_chapter.py <url>` to pull a chapter, see "Per-chapter workflow"). Open with a `#### Title` block carrying the book name and a `#### Subtitle` block carrying the short reign-statement, then one `#### Sentence N` (h4) heading per sentence in the book-level summary paragraph, splitting on `.`. Each sub-block carries one backtick'd Persian sentence, a `[gloss]` line, an `[en]` translation, and then the vocab it introduces. If a sentence introduces no new lemmas, emit the heading, backtick'd Persian, gloss, `[en]` line, and then the italic note `_(No new lemmas — every word in this sentence has already been introduced.)_` in place of a vocab list. Use underscores (not asterisks) so `render.py` renders it as `<em>` rather than bold.
  - **Chapter summary** — `### Chapter summary` (h3) followed by the entire summary text on a single line wrapped in backticks, a `[gloss]` line, an `[en]` translation, and then a single flat vocab list for the whole summary.
  - **Each verse** — `### Verse N` (h3) followed by the entire verse text on a single line wrapped in backticks, a `[gloss]` line, an `[en]` translation, and then a single flat vocab list for that verse.
  - **Editorial ezafe marker `{e}`**. The Persian Book of Mormon source very rarely writes the unstressed ezafe linker (`-e` / `-ye`) on consonant-final words — the reader is expected to know to pronounce it. To help learners, insert a literal `{e}` in the markdown source at every site where ezafe is unwritten in the source text or in a grammar-example blockquote. `render.py` converts each `{e}` to `<span class="ezafe">ِ</span>` (a kasra wrapped in a styled span); CSS colors the kasra in the project's accent color and slightly bolds it, so the reader can see at a glance that this kasra was added by us — _not_ part of the publisher's text. Examples:
    - `کتاب{e} نیفای` → _ketāb-**e** Nīfāy_ "the Book of Nephi" (the rendered HTML attaches the kasra to ب and styles it).
    - `سرزمین{e} اورشلیم` → _sarzamīn-**e** Uršalīm_ "the land of Jerusalem".
    - `بدنبال{e} نابودی{e} زندگی{e} او` → _bedonbāl-**e** nābūdī-**ye** zendegī-**ye** ū_ "in pursuit of the destruction of his life" — chained ezafes, all editorial.

    Where ezafe is **already visible in the source spelling**, do **not** add `{e}`. Visible cases:
    - `ۀ` on words ending in silent `ه` (e.g. `نگاشتۀ پدرم`, `همۀ مردم`).
    - `ی` on words ending in long `ا` / `و` (e.g. `خدای قادر`, `روی زمین`).
    - `های` (plural + ezafe) on plural-marked nouns (e.g. `رحمت‌های مهرآمیز`).
    - The very rare explicit kasra the publisher wrote in the original (e.g. `کتابِ نبوّت` in the chapter summary). Leave that kasra alone — keeping it unstyled signals that it was already in the source.

- **English translation (`[en]`)**. Write the official LDS English edition text (or a close equivalent) on a line by itself immediately after the `[gloss]` line:

  ```
  [en] The First Book of Nephi
  ```

  The renderer wraps this in `<div class="translation translation-en">` and hides it by default. It becomes visible when the reader checks the **Translation** toggle. Use `[lit]` instead of `[en]` for a word-for-word literal gloss when the idiomatic English would obscure the Persian structure.

- **Interlinear gloss (`[gloss]`)**. Write the gloss line immediately after the backtick'd source text and before the `[en]` line. Each token is `source|gloss` pairs separated by spaces, following [Leipzig Glossing Rules](https://www.eva.mpg.de/lingua/resources/glossing-rules.php):

  ```
  [gloss] noxostīn|first ketāb=e|book=EZ Nīfāy|Nephi
  [gloss] yek|1 man|1SG Nīfāy|Nephi az|from pedar|father o|and mādar=e|mother=EZ xūb-ī|good-INDEF zāde|bear-PTCP.PST šode|become-PTCP.PST
  ```

  **Source slot** (left of `|`): romanized transliteration of the Persian word, with morphological boundaries marked per Leipzig Rule 2:
  - **Hyphens (`-`)** for bound morphemes (affixes attached to the host): `hamsar-aš` (wife+3SG.POSS), `šod-and` (become+PST.3PL), `kāmel-ī` (complete+INDEF).
  - **Equals signs (`=`)** for clitics (phonologically attached but syntactically independent): `ketāb=e` (book=EZ), `sarzamīn=e` (land=EZ). Ezafe is always a clitic.
  - Boundaries in the source slot must match the segmentation shown in the gloss slot. A hyphen in the gloss (e.g. `wife-3SG.POSS`) requires a hyphen at the same position in the source (`hamsar-aš`).
  - Words written separately in Persian that are separate tokens in the gloss get no boundary marker even if they are grammatically dependent — e.g. `mī|IMPF deh-ad|give-PRS-3SG` (می and دهد are separate written words).

  **Gloss slot** (right of `|`):
  - Lexical content in **lowercase**: `book`, `first`, `become`, `father`.
  - Grammatical abbreviations in **UPPERCASE** (rendered as small caps): `EZ`, `PST`, `3SG`, `PL`, `IMPF`.
  - Multi-part labels joined with `.`: `3SG.POSS`, `PTCP.PST`, `NEG.IMPF`.
  - Morpheme boundaries with `-`: `wife-3SG.POSS`, `book-INDEF`, `give-PRS-3SG`.
  - Clitic boundaries with `=`: `book=EZ`, `in.pursuit=EZ`.
  - Multi-word English glosses use `.` to join them (no spaces within a token): `in.pursuit`, `so.that`, `that.which`.

  **Standard abbreviations** used in this project:

  | Abbrev | Meaning | Example |
  |--------|---------|---------|
  | `ACC` | accusative (`را`) | `rā\|ACC` |
  | `CL` | classifier / counter | `tā=ye\|CL=EZ` |
  | `COMP` | complementizer `که` (introducing a clause) | `ke\|COMP` |
  | `COP` | copula (`است`, enclitic `-am/-ī/…`) | `ast\|COP-3SG` |
  | `EZ` | ezafe linker (`-e`/`-ye`) | `ketāb=e\|book=EZ` |
  | `FUT` | future auxiliary (`خواه-`) | `xāh-am\|FUT-1SG` |
  | `IMPF` | imperfective prefix (`می-`) | `mī\|IMPF` |
  | `INDEF` | indefinite suffix (`-ī`) | `ketāb-ī\|book-INDEF` |
  | `INF` | infinitive (base form used with `خواستن` future) | `negāšt\|write-INF.PST` |
  | `INF.PST` | past-stem infinitive (short infinitive used in future constructions) | same as above |
  | `NEG` | negative prefix (`نـ-`, `نه-`) | `na-xāh-am\|NEG-FUT-1SG` |
  | `NARR` | narrative suffix (`-ā` on گفتا) | `goft-ā\|say-NARR` |
  | `PASS` | passive (analytical: pp + شدن) | `šav-ad\|become-PASS-3SG` |
  | `PL` | plural (`-hā`) | `hā=ye\|PL=EZ` |
  | `POSS` | possessive enclitic | `hamsar-aš\|wife-3SG.POSS` |
  | `PRS` | present tense | `kon-ad\|do-PRS-3SG` |
  | `PRV` | preverb (separable prefix, e.g. `بر-` in `برمی دارد`) | `bar-mī\|PRV=IMPF` |
  | `PST` | past tense | `kard\|do-PST-3SG` |
  | `PTCP` | participle | `xānde\|call-PTCP.PST` |
  | `REL` | relative particle `که` | `ke\|REL` |
  | `SBJV` | subjunctive | `šav-and\|become-SBJV-3PL` |
  | `SG` | singular | (used in person+number combos: `1SG`, `3SG`) |
  | `VOC` | vocative | `Sarvar-ā\|Lord-VOC` |

  Person and number are written together without a separator: `1SG`, `2PL`, `3SG`, `3PL` (Leipzig Rule 5).

  **Persian numerals**: use the spelled-out transliteration as the source token: `yek|1`, `do|2`, `se|3`, `čahār|4`, `panj|5`, `šeš|6`, `haft|7`, `hašt|8`, `noh|9`, `dah|10`, `yāzdah|11`, `davāzdah|12`, etc. For larger numbers in a title or heading context (e.g. `600 B.C.`) use the Arabic numeral: `600|600`.

  The renderer hides the gloss block by default; it becomes visible when the reader checks the **Gloss** toggle. Words flow left-to-right (the transliteration line reads in sentence order, first word on the left).

- **Order of first appearance**. A word appears once, in the verse where the reader first encounters it.
- **Lemmatize**: one entry per lemma (infinitive for verbs, singular citation form for nouns). Do **not** re-list a later inflected form (e.g. a new past-tense) as a fresh entry — forms are handled by the present-stem / past-participle notes on the original entry.
- **Scope**: every distinct lemma in the chapter, including function words.
- **Proper nouns**: mix inline where they first appear, tagged with `[proper]`.
- **Persian numerals** (`۰ ۱ ۲ ۳ ۴ ۵ ۶ ۷ ۸ ۹`): give every numeral that appears in the chapter its own vocab entry, in order of first appearance, with the digit form as the **headword**, the cardinal pronunciation as the transliteration, and the spelled-out Persian word in backticks. Format:

  ```
  **۲** — *do* — Persian numeral 2 (`دو`)
  **۱۲** — *davāzdah* — Persian numeral 12 (`دوازده`)
  **۶۰۰** — *šešṣad* — Persian numeral 600 (`ششصد`)
    - *Etym*: `شش` *šeš* "six" + `صد` *ṣad* "hundred".
  ```

  Every numeral gets its spelled-out form in `(backticks)` after the gloss — that's how the reader practices reading the digit. Do **not** cross-reference cardinal-word entries that happen to be elsewhere in the vocabulary (e.g. don't write "digit form of `سه`, an entry in the book summary"); the spelled form in the parenthetical is enough on its own. Conventions:
  - Single digits get the bare cardinal pronunciation; no `*Etym*` (native Persian).
  - **Teens 10–19 are unique words**, not "one-zero", "one-one", etc. — flag this on `۱۰` (e.g. ``Persian numeral 10 (`ده` — a single word, not "one-zero")``).
  - **Multiples of ten** likewise have unique forms — flag on `۲۰` (``Persian numeral 20 (`بیست` — a separate word, not "two-zero")``).
  - **Hundreds and beyond** are compound — give the morpheme breakdown in `*Etym*` (e.g. for `۶۰۰`, `\`شش\` + \`صد\` "hundred"`).
  - Verse numbers count as appearances, so each verse opens its vocab list with its own number's entry (the digit at the start of the inline source text). A prose note saying "see the earlier `۶۰۰` entry" is **not** sufficient — a digit that appears as a standalone token in a source-text block must have its own headword entry so `render.py` can link it.
  - **First numeral meta-note**: the very first numeral entry in a chapter (typically the digit that opens verse 1) should include a `*Forms*` sub-bullet explaining the digit system to the learner: that each digit's pronunciation is introduced at first appearance, and that teens and multiples of ten are single unanalysable words, not digit-by-digit composites. This meta-note appears on the first numeral entry only; subsequent numeral entries in the same chapter do not repeat it.

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

  **Backtick variant entries** — Literary/archaic forms, grammatical variants, and surface forms that are *not* the citation-form lemma use a backtick headword instead of bold:

  ```
  - `گفتا` (_goftā_) — archaic narrative past of `گفتن`; see [Grammar: Narrative -ā](#grammar-narrative)
  - `سرورا` (_Sarvarā_) — vocative of `سرور`; see [Grammar: Vocative -ā](#grammar-vocative)
  ```

  Use backtick entries when the entry IS the form itself (not a dictionary citation form). When a backtick entry is a grammatical variant of a bold entry already in the same section, add a cross-reference to the parent entry or its grammar note.

- **Bound morpheme entries** — Productive bound morphemes (suffixes or prefixes that appear only in compounds) get their own entry with `[bound morpheme]` in the gloss:

  ```
  - **انگیز** — _angīz_ — arousing [bound morpheme]
    - _Etym_: present stem of `انگیختن` _angixtan_ "to arouse, excite".
    - _Family_: `شورانگیز` _šur-angīz_ "stirring, exciting"; `هیجان‌انگیز` _hayajān-angīz_ "thrilling".
  ```

- **Metadata sub-bullets** (the `*Etym*`, `*Forms*`, and `*Family*` lines under a vocab entry). Keep the headline of an entry **clean** — just `**Persian** — *translit* — meaning [maybe a one-word register tag like "literary"]`. Anything more goes in nested bullets directly underneath:

  ```markdown
  - **شادمانی** — _šādmānī_ — joy, gladness
    - _Etym_: `شاد` + `-مان` (adjectival) + `-ی` (abstract).
    - _Family_: `شاد` _šād_ "happy"; `شادمان` _šādmān_ "joyful, cheerful".
    - _Forms_: collocation `شادمانی کردن` "to rejoice".
  ```

  Each italic label (`*Etym*`, `*Forms*`, `*Family*`) at the start of a sub-bullet is recognized by `render.py` and rendered as a small chip-style tag in HTML. All labels are optional — include each one only if it actually has content. Indent sub-bullets with **two spaces**.

  **Inline Persian in meta sub-bullets always uses backticks.** Every Persian word or morpheme fragment (including prefix/suffix notation like `` `-ی` `` and `` `نا-` ``) must be wrapped in backtick code spans. This applies to all three label types equally — `*Forms*` was already consistent; `*Etym*` and `*Family*` must follow the same rule. The backtick styling gives Persian text a legible size and a distinct background that makes it easy to pick out from the surrounding Latin transcription and English gloss. The headword in the vocab entry headline (`**Persian**`) is exempt — it gets its own larger `.persian` styling instead.

- **When to add `*Etym*`** (etymology / morpheme breakdown — included only when the answer is interesting):
  - **Arabic loanwords** — common in religious/literary register. Note the source language and, when easy to identify, the triliteral root. Example: `*Etym*: from Arabic, root r-ḥ-m "compassion"`.
  - **Compounds with meaningful morphemes** — break down the parts. Example: ``*Etym*: `سر` *sar* "head" + `گذشت` *gozašt* "past" (← `گذشتن` "to pass"); literally "what passed at one's head".``
  - **Proper nouns of foreign origin** — Hebrew (most BoM names via Arabic / English transliteration), or English (BoM-coined). Example: `*Etym*: Hebrew יהודה *Yəhūdā* "praised", via Arabic`.
  - **Native, non-compound Persian words** — _do not_ add `*Etym*`. Don't write "native Persian"; absence is the signal.

  **Morpheme-breakdown notation**: wrap every fragment in backticks. Use `→` with a quoted literal to spell out the compositional meaning: `` `نا-` + `بکار` + `-ی` → "non-useful-ness" ``; use `←` to trace a form back to its source verb or root: `` `گذشت` ← `گذشتن` "to pass" ``.

- **When to add `*Family*`** (related words to memorize alongside this entry — different from `*Etym*`, which is the linguistic breakdown):
  - When the entry's stem is **a useful Persian word in its own right** that doesn't otherwise appear in the chapter. Example: `شادمانی` is in the chapter, but seeing `شاد` "happy" and `شادمان` "joyful" listed alongside lets the reader pick up three vocabulary items for the price of one.
  - When the entry has **derivational siblings** the reader will meet later (e.g., `شورش` "rebellion" → list `شور` "fervor" and `شوریدن` "to revolt"; `ستایش` "praise" → list the source verb `ستودن`).
  - For **compounds** whose components are themselves vocabulary worth memorizing (e.g., `سرگذشت` → `سر` "head" + `گذشتن` "to pass"; both are headwords elsewhere in this chapter, but the Family note re-lists them with brief glosses for quick reference).
  - When a related form listed in `*Family*` is **superficially similar to an unrelated word**, add a parenthetical disambiguation: e.g. `` `کوهسار` _kūhsār_ "mountainous place" (note: the `-سار` here is the native "place-of" suffix; cf. `سنگسار` "stoning", which contains a homophonous but likely unrelated _-sār_) ``.

  Format: short list with each related form's translit and a one-or-two-word gloss, separated by `;`. Example: ``*Family*: `شاد` *šād* "happy"; `شادمان` *šādmān* "joyful".`` Don't repeat the entry's headword; don't repeat detail already in `*Etym*`.

- **When to add `*Forms*`** (morphology, conjugation, common collocations):
  1. **Verbs whose surface forms in the chapter would surprise a learner**. Always include `*Forms*` for:
     - **Suppletive present stems** (no shared consonants with infinitive): `دیدن` (pres. `bīn-` → _می بیند_), `آمدن` (pres. `ā-` → _می آید_, with epenthetic `-y-`), `دادن` (pres. `deh-` → _می دهد_), `رفتن` (pres. `rav-` → _رود_, where `rav-` + `-ad` collapses in spelling).
     - **Conjugation quirks**: `داشتن` drops `می-` in the present indicative (_دارد_ / _دارند_, never `می‌دارد`). Prefixed compounds of داشتن reverse this: `می-` slots **between** the prefix and داشتن (_برمی دارد_). Compound-verb subjunctives routinely drop the `بـ-` (`توانا سازد` ≈ `توانا بسازد`).
     - **Auxiliary uses**: `خواستن` as future auxiliary (_خواهم نگاشت_, …); `شدن` as passive auxiliary (_خوانده می شدند_, …).
     - **High-frequency verbs that show up in many shapes** (`بودن`, `شدن`, `کردن`, `داشتن`, `دادن`): summarize the paradigm visible in this chapter (3sg, 3pl, past, pp).
  2. **Common collocations or related compound forms** of any lemma — what would have been an inline parenthetical (e.g., on `دنبال`, the pair `به دنبال` / `بدنبال`; on `خشم`, the verb `خشم گرفتن`). Move these to `*Forms*:` instead of the headline.
  3. **Regular verbs** whose past stem matches the infinitive transparently (`زادن` → `زاد`/`زاده`, `شنیدن` → `شنید`/`شنیده`, etc.) — add `*Forms*` listing the backtick'd conjugated forms that actually appear in the chapter's source text. This is required for `render.py` to link those surface forms back to the headword. If none of the regular verb's forms appear in source-text lines, the `*Forms*` sub-bullet can be omitted.
  4. **Web-edition orthography** — when the publisher's web text writes a word with diacritics that differ from the citation form used in this guide, note it in `*Forms*`: `` _Forms_: web edition writes `سَروَر`; unmarked `سرور` is the citation form used here. ``

  Inside `*Forms*`, cite **verbatim Persian from the source text with a section reference** so the anchor is checkable. Format: `*Forms*: 3sg pres. *surface translit*, as in \`phrase\` "English", [verse N](#verse-n); past _…_; pp. _…_.` Use `[chapter summary](#chapter-summary)`, `[verse N](#verse-n)`, or `[book summary, sentence N](#sentence-n)` as appropriate. The backtick-quoted forms in `*Forms*` are harvested by `render.py` when building the source-text link map — every form you list in backticks will become a clickable link in the inline source-text blocks.

  **Token registration rules — what needs an explicit backtick entry.** `render.py` tokenizes source text on whitespace. A token is linked if it (a) exactly matches a headword, (b) matches after stripping common diacritics, or (c) appears as a standalone backtick token in any `*Forms*` sub-bullet. Fallback (b) strips harakat-range marks (U+0610–U+061A, U+064B–U+065F) but **not** `ۀ` (U+06C0). The practical consequences — all require explicit `*Forms*` backtick registration:

  - **Ezafe forms ending in `ۀ`** — `کرانۀ`, `دهانۀ`, `همۀ`, `پایۀ`, `سرچشمۀ`, etc. are not stripped to their base and need a standalone backtick entry such as `` `کرانۀ` _karāne-ye_ (ezafe form) ``.
  - **Backtick phrases with spaces** — `` `می گوید` `` inside a `*Forms*` bullet registers only as a two-token phrase; it does **not** register `گوید` as a standalone token. If `گوید` (or any component) appears as a bare token in source text, add a standalone `` `گوید` `` backtick entry on the same or another `*Forms*` line.
  - **Fused possessive/clitic forms** — `گرانبهایش`, `گرانبهایشان`, `خانواده اش` (written with space) etc. are separate surface forms. Add them explicitly when they appear: `` `گرانبهایش` _gerān-bahā-yaš_ (3sg poss.) ``.
  - **Negative verb forms** — `نداشتند`, `نبرد`, `نخواستند` are not auto-derived from the positive form. List them in `*Forms*` with their negation noted.
  - **Comparative suffix `-تر`** — `نزدیکتر`, `بیشتر`, etc. are not auto-resolved from the adjective. Add as `` `نزدیکتر` _nazdīk-tar_ "nearer" `` in `*Forms*`.
  - **Subjunctive 3pl `-اند`** — `شوند`, `بدانند`, etc. won't match the infinitive headword. List them when they appear.
  - **`می` and `نمی` as standalone tokens** — the publisher writes the imperfective prefix with a space before the verb stem (`می بَرد`, `نمی گفت`), making `می` a separate whitespace-delimited token. Do **not** give `می` or `نمی` their own headword entries — they are part of the verb. The renderer automatically wraps `می`/`نمی` + the following verb token as one `<a>` link to the verb's anchor. In `*Forms*` sub-bullets, write them together in a single backtick group: `` `می بَرد` `` (not `` `می` `بَرد` ``).

  **Multi-word (bigram) linking.** `render.py` tries a two-token bigram lookup before falling back to a single-token lookup. When two consecutive Persian tokens separated by a single space match a `*Forms*` entry (or headword) that contains a space — e.g. `` `نگه دارند` `` registered under `**نگه داشتن**`, or `` `دریای سرخ` `` registered under `**دریا**` — both tokens are wrapped in a single `<a>` link to the headword anchor. This means: **for compound verbs and fixed multi-word phrases, list the relevant surface forms as backtick tokens in `*Forms*` even when they contain a space**, and the linker will handle them as a unit. Bigrams take priority over single-token matches, so if `` `نگه دارند` `` is registered, `نگه` and `دارند` will not be linked individually.

  **Unlinked-word warnings.** After `build_site.py`, `render.py` emits `unlinked:` warnings to stderr for any source-text token it could not map to a vocab entry, with a count and the section names where each unlinked token appears (e.g. `ch2.md: unlinked: کرانۀ — Verse 5`). Treat every warning as a missing `*Forms*` backtick entry or missing headword and fix before pushing.

  **Multi-tense stacking**: a single `*Forms*` line may list several tense/mood/person forms separated by semicolons, in order: morphophonological note first (if any), then present, then past, then imperfect, then past participle. Each form cites the verse where it first appears: `3sg pres. \`می آید\` mī-āyad ([verse 9](#verse-9)); past \`آمد\` āmad`.

  **Correlative patterns**: for words used in fixed paired constructions, document with ellipses: `` _Forms_: correlative `هم … هم …` "both … and …". ``

  **Inline explanatory parentheticals**: `*Forms*` lines may include a parenthetical when a surface form departs from the expected paradigm: e.g. "bare `دهد` is classical/literary or a compound-verb subjunctive with `بـ-` dropped."

- **Irregular reading warnings (⚠️)**: flag Arabic loanwords whose Persian spelling would mislead a learner into a wrong pronunciation. Place the ⚠️ sub-bullet **first** under the headword, before any `*Etym*` line — and only on the sub-bullet, never on the headword line itself:

  ```markdown
  - **حتّی** — _ḥattā_ — even
    - ⚠️ _Alif maqṣūra_: the final `ی` represents Arabic _alif maqṣūra_ (`الألف المقصورة`) — a long -ā vowel written `ى` at the end of certain Arabic words. Learners may accidentally read it as _\*ḥattī_.
    - _Etym_: from Arabic _ḥattā_, originally a preposition "until, up to".
  ```

  Rules:
  - One ⚠️ only — on the sub-bullet. No ⚠️ on the headword line.
  - The italic label names the specific phenomenon. Keep the explanation to one sentence; end with `Learners may accidentally read it as _\*wrongform_.` (the `\*` is the standard linguistic convention for an incorrect form; it renders as a literal asterisk in HTML).
  - Persian in backticks; transcriptions in italic underscores.
  - In HTML, render.py assigns these bullets `.vocab-meta-other` (the ⚠️ precedes any italic label, so the label-detection regex does not match).

  Common categories:

  | Label                           | When to use                                                                                         |
  | ------------------------------- | --------------------------------------------------------------------------------------------------- |
  | `_Alif maqṣūra_`                | Arabic final ى — written ی in Persian — is read -ā, not -ī (e.g. `حتّی` _ḥattā_ "even").            |
  | `_Diphthong -ay- written as ی_` | Arabic _-ay-_ diphthong where learners expect Persian long _-ī-_ (e.g. `علیه` _ʿalayhi_ "against"). |

### Grammar notes

Grammar notes live **inline in the vocabulary section**, immediately after the vocab entry for the primary word they explain. They appear in source order (earliest first appearance determines placement). Use a `>>>` fence:

```
>>>
Grammar: [title]

[body: 1–3 sentence explanation, then blockquote examples]

> [Verse N](#verse-n): `Persian text`
> _transliteration_
> English translation
>>>
```

The renderer wraps the block in `<div class="grammar-note-block">` and renders the title as a styled `<h4 class="grammar-note">`. Note: `>>>` must appear on its own line; the line immediately after the opening `>>>` is the block title.

Example sentence **must be taken verbatim from the chapter's source text** — no invented examples. A grammar note may include an **inline comparison** between two verses to contrast constructions: `Also compare [Verse N](#verse-n): \`phrase\` (_reason_) with \`phrase\` (_reason_).` Grammar notes do **not** get a separate `## Grammar notes` section; they are woven into the vocab lists.

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

### Closing section

Every chapter ends with a `## A final note on reading strategy` heading (H2), followed by one short paragraph naming the key grammar constructions that appeared in the chapter (e.g. "This chapter introduces the `چنین گذشت` narrative formula, the subjunctive after `تا`, and the compound-verb `بـ-` drop") and one study-tip sentence (e.g. "Before moving on, try reading the chapter summary aloud, paying attention to the ezafe chains").

## HTML rendering

`render.py` converts a chapter's Markdown study guide into semantic HTML and links it to `styles.css`. The goal is a readable on-screen reading copy that also prints to PDF cleanly, with Persian text set in a proper Persian font at a legible size and code/example blocks high-contrast. `build_site.py` invokes `render()` for every `study_guide/NN_book/chN.md` it finds, drops the result under `_site/study_guide/NN_book/chN.html`, and emits a top-level `_site/index.html` that lists all chapters and gives the source publication's original title and copyright.

```bash
python3 build_site.py                                          # full site → _site/
python3 render.py study_guide/NN_book/chN.md /tmp/x.html      # one-off single-file render
```

The HTML document structure is standard: `<main>` wraps the body; headings are `<h1>/<h2>/<h3>`; paragraphs are `<p>`; nested lists are rendered as properly-nested `<ul>/<li>`. The semantic elements unique to this project get classes from a small fixed taxonomy:

| Class               | Applied to | Where it comes from in Markdown                                                                                                         |
| ------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `.vocab`            | `<ul>`     | Any bullet list that contains at least one item with a bold Persian headword (treated as a vocab list; tolerates mixed bold/code items). |
| `.vocab-entry`      | `<li>`     | Each item inside a `.vocab` list; gets `id="vocab-HEADWORD"` (the raw Persian headword) so `.src-link` anchors resolve.                 |
| `.vocab-meta`       | `<ul>`     | Sub-list directly inside a `.vocab-entry` (the `Etym` / `Forms` block).                                                                 |
| `.vocab-etym`       | `<li>`     | Item in `.vocab-meta` whose label is `*Etym*` or `*Etymology*`.                                                                         |
| `.vocab-forms`      | `<li>`     | Item in `.vocab-meta` whose label is `*Forms*` or `*Form*`.                                                                             |
| `.vocab-family`     | `<li>`     | Item in `.vocab-meta` whose label is `*Family*` or `*Kin*`.                                                                             |
| `.vocab-meta-other` | `<li>`     | Fallback class on a `.vocab-meta` item with an unrecognized leading label.                                                              |
| `.meta-label`       | `<span>`   | The `Etym` / `Forms` chip at the start of a meta sub-bullet (rendered as a small uppercase tag).                                        |
| `.persian`          | `<strong>` | The bolded Persian headword at the start of a vocab entry.                                                                              |
| `.translit`         | `<em>`     | The first italic span in a vocab entry (the transliteration after the headword).                                                        |
| `.proper`           | `<span>`   | The literal text `[proper]` inside a vocab entry (tag for proper nouns).                                                                |
| `.example`          | `<div>`    | Replaces `<blockquote>`. Any Markdown blockquote is treated as a three-line grammar example.                                            |
| `.example-fa`       | `<div>`    | First line of an example — Persian + (optional) line-ref prefix. Uses `direction: ltr; text-align: left` so the `.line-ref` label (first in DOM) is placed on the left; the `<code>` inside uses `direction: rtl; unicode-bidi: embed` so the Persian text still renders right-to-left. Do **not** change `.example-fa` to `direction: rtl` — that causes the bidi algorithm to place the first DOM element (the label) on the visual right, reversing the intended label-then-Persian order. |
| `.example-tr`       | `<div>`    | Second line of an example — italic transliteration.                                                                                     |
| `.example-en`       | `<div>`    | Third line of an example — English translation.                                                                                         |
| `.line-ref`         | `<span>`   | The section-reference prefix at the start of `.example-fa` (e.g. `[Verse 4](#verse-4):`).                                               |
| `.source-text`      | `<p>`      | Wraps a standalone backtick-quoted source line (`<p class="source-text"><code>…</code></p>`); triggers the block Persian display style.  |
| `.src-link`         | `<a>`      | A Persian word inside a `.source-text` `<code>` block linked to its vocab or grammar entry anchor.                                       |
| `.translation`      | `<div>`    | An `[en]` or `[lit]` paragraph; hidden by default, shown when the **Translation** toggle is checked.                                    |
| `.translation-en`   | `<div>`    | Added alongside `.translation` for `[en]` lines (official English text).                                                                |
| `.translation-lit`  | `<div>`    | Added alongside `.translation` for `[lit]` lines (word-for-word literal gloss).                                                         |
| `.gloss`            | `<div>`    | The entire interlinear gloss block for a `[gloss]` paragraph; hidden by default, shown when the **Gloss** toggle is checked.            |
| `.gloss-words`      | `<div>`    | Flex container inside `.gloss`; words flow left-to-right in sentence order.                                                             |
| `.gloss-unit`       | `<div>`    | One source+gloss pair (a single token column): stacks `.gloss-src` above `.gloss-tag`.                                                  |
| `.gloss-src`        | `<span>`   | The transliteration (source line) inside a gloss unit.                                                                                  |
| `.gloss-tag`        | `<span>`   | The Leipzig gloss label inside a gloss unit.                                                                                            |
| `.gl`               | `<span>`   | A Leipzig abbreviation (2+ consecutive capitals, or digit+caps) inside `.gloss-tag`; rendered in small caps.                            |
| `.toggle-bar`       | `<div>`    | The row of toggle switches injected before each source-text block; contains up to three toggles (ezafe, translation, gloss).            |
| `.grammar-note-block` | `<div>`  | Wrapper for a `>>>` grammar fence block; light-blue background with left border.                                                        |
| `.grammar-note`     | `<h4>`     | The title heading inside `.grammar-note-block`; styled in small caps with a darker header band.                                         |
| `.ezafe`            | `<span>`   | An editorial kasra injected by `{e}` in the Markdown source; colored to distinguish it from the publisher's text.                       |
| `<h3>`              | (element)  | Section heading (`### Verse 1`); gets `id="verse-1"` (slugified) so source-text word links can point into it.                           |
| `<h4>`              | (element)  | Sentence / line marker (`#### Sentence 3`, `#### Title`); styled small/uppercase with a dashed top rule for sub-blocks under a section. |

The parser is deliberately narrow: it handles headings (with auto-generated `id` slugs), paragraphs, bold/italic/inline-code, Markdown links (`[text](url)`), nested `- ` bullet lists, `> ` blockquotes, and `>>>` grammar-note fences. It does not handle tables or code fences. Standalone backtick paragraphs (a paragraph whose entire content is a single backtick-quoted string) are treated as source-text quotations and emitted as `<p class="source-text"><code>…</code></p>`; each Persian token is looked up in the vocab map and, if found, wrapped in a `.src-link` anchor. Grammar-note fences (`>>>` on its own line) open a `<div class="grammar-note-block">` whose first non-blank line becomes the `<h4 class="grammar-note">` title; a second `>>>` closes the block. If a future chapter needs richer Markdown, swap in [python-markdown](https://pypi.org/project/Markdown/) or [markdown-it-py](https://pypi.org/project/markdown-it-py/) (add a `requirements.txt` and a venv) and keep the post-processing step that injects the classes above.

### Editing the stylesheet

`styles.css` lives at the project root so every chapter shares one visual identity. Adjust colors, font stacks, or sizes there once and every chapter re-renders with the new look — the HTML doesn't need to change. Print styling lives in `@media print` at the bottom of the file.

## Running the toolchain

```bash
# From the project root, for book directory study_guide/NN_book/:
python3 fetch_chapter.py <url> -o study_guide/NN_book/web.txt    # pull a chapter from the web
python3 build_site.py                                              # render every chN.md → _site/
python3 check_links.py                                             # verify all in-page anchor links resolve
```

`check_links.py` scans every HTML file in `_site/` and reports any `href="#..."` whose target `id="..."` does not exist in the same file. Run it after `build_site.py` to catch broken vocab links before pushing. Exits 0 if everything is clean, 1 if any broken links are found.

No dependencies beyond the Python 3.10+ standard library. CI runs `python3 build_site.py` and publishes `_site/` to GitHub Pages on every push to `main`/`master`; see `.github/workflows/pages.yml`.

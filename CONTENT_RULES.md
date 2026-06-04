# Content Rules for Persian BoM Study Guides

These rules govern editorial decisions when producing a chapter study guide — what to include, how to explain it, and what to annotate. Chapter study guides are authored as `chN.source.json` + `chN.study.json` (see [GENERATING_CHAPTERS.md](GENERATING_CHAPTERS.md) for the workflow). The reference pages (`verbs.md`, `word_formation.md`, etc.) are hand-authored Markdown and are not covered by these rules.

---

## Guiding principles

**Standalone per chapter.** Every chapter is self-contained. Re-introduce all vocabulary and grammar constructions even if a prior chapter already covered them. A reader starting at chapter 5 must be able to use chapter 5's guide without referring to chapters 1–4.

**Order of first appearance.** Within a chapter, words are introduced in the order the reader first encounters them in the source text (book summary → chapter summary → verses). A word appears exactly once, in the section where it first appears.

**Lemmatize.** One entry per lemma: infinitive for verbs, singular citation form for nouns. Handle inflected forms in the `forms` array of the original entry; do not create a separate headword for each inflection.

---

## Intro section

The `intro` field at the top level of `study.json` is one short paragraph (~½ page) summarizing the chapter's narrative content: what happens, who speaks, what key themes appear. Supports inline Markdown. Keep it descriptive and concise.

**Language: English.** The `intro` and `reading_tip` fields are study-aid prose written for the learner and must always be in English, not Persian.

---

## Scope: which words to include

Include every distinct lemma in the chapter, including function words. Every chapter is standalone, so nothing can be assumed from prior chapters.

**`می` and `نمی` are never headwords.** The imperfective prefix is always treated as part of the verb it modifies. The renderer automatically wraps a `می`/`نمی` source token + the following verb token as a single linked unit. In the `forms` array, write them together in a single `fa` value: `"می بیند"` (not two separate items).

**Proper nouns.** Every proper noun gets its own headword entry with `"pos": "propn"` and `"tags": ["proper"]`. Include an `etym` object when the name has an interesting linguistic background (Hebrew, Arabic, English transliteration, etc.).

---

## Headword entries

Each headword entry in a study section's `entries` array is a JSON object with `"type": "headword"`.

Required fields on every headword:

| Field | Description |
|---|---|
| `persian` | Lemma (infinitive for verbs; singular for nouns/adjectives; citation form for everything else) |
| `translit` | Romanization |
| `meaning` | English gloss — keep concise; do not embed etymology, collocations, or commentary here |
| `pos` | Part of speech (see below) |

Optional fields: `id` (anchor id; defaults to `persian` with spaces replaced by `_`), `tags`, `pres_stem` (verbs), `plural` (nouns), `light_verb`, `etym`, `family`, `forms`, `warning`.

### Part of speech (`pos`)

Use the [Universal Dependencies](https://universaldependencies.org/u/pos/) UPOS tags (lowercase). Common values for this project:

| Value | Use for |
|---|---|
| `noun` | Common nouns, including abstract and mass nouns |
| `verb` | Verbs |
| `aux` | Auxiliary verbs (شدن as passive aux, خواستن as future aux) |
| `adj` | Adjectives |
| `adv` | Adverbs |
| `adp` | Adpositions / prepositions (از، به، با، بر، در) |
| `cconj` | Coordinating conjunctions (و، یا) |
| `sconj` | Subordinating conjunctions (که، چون، زیرا، تا "so that") |
| `pron` | Pronouns |
| `num` | Numerals |
| `part` | Particles (را، the بـ- prefix, etc.) |
| `propn` | Proper nouns |
| `intj` | Interjections (آری، وای) |
| `det` | Determiners (همه، هر) |

The renderer prints warnings to stderr when:
- `pos` is missing from any headword
- `pos="verb"` and `pres_stem` is absent
- `pos="noun"` and `plural` is absent

### `pres_stem` (verbs)

Required for all verbs. Object with `fa` (Persian present stem) and `translit`:
```json
"pres_stem": { "fa": "نگار", "translit": "negār-" }
```
Set `fa` to `null` only when the present stem has no distinct Persian spelling (e.g. it is always written with `می-` and the stem alone never appears in isolation).

### `plural` (nouns)

Include `plural` for all nouns (it may appear alongside `light_verb`). Object with `suffixes` and/or `broken` arrays. List suffix forms first, broken (Arabic) plurals second. A noun can have multiple suffix variants (e.g. a formal and a colloquial form):

```json
"plural": {
  "suffixes": [
    { "persian": "برادران", "translit": "barādarān", "note": "standard" },
    { "persian": "برادرها", "translit": "-hā", "note": "colloquial" }
  ]
}
```

```json
"plural": {
  "suffixes": [{ "persian": "خدمت‌ها", "translit": "-hā" }],
  "broken": [{ "persian": "خدمات", "translit": "xadamāt", "note": "standard formal" }]
}
```

### Light-verb constructions (`light_verb`)

If a noun can function as the pre-verbal element of a light-verb construction, add `light_verb` to the noun entry — even if that construction doesn't appear in the chapter's source text. Do **not** also list the compound in `forms` — `light_verb` gets its own rendered line:
```json
"light_verb": [{ "verb": "کردن", "translit": "kardan", "meaning": "to repent" }]
```

---

## Numerals

Give every numeral that appears in the chapter its own headword entry, in order of first appearance. Use the digit form (e.g. `"۲"`) as `persian`, the cardinal pronunciation as `translit`, and include the spelled-out Persian word in `meaning` (e.g. `"Persian numeral 2 (دو)"`).

- **Single digits**: bare cardinal pronunciation; no `etym` (native Persian).
- **Teens 10–19**: unique words, not digit-by-digit composites. Flag this in `meaning`, e.g. `"Persian numeral 10 (ده — a single word, not \"one-zero\")"`.
- **Multiples of ten** (`۲۰`, `۳۰`, …): likewise unique words; flag in `meaning`.
- **Hundreds and above**: compound forms — give the morpheme breakdown in `etym.prose`.
- **Verse numbers count as first appearances.** Each verse's opening digit needs its own entry.
- **First numeral meta-note.** The very first numeral entry in a chapter should include a `forms` item with a `note` key explaining the digit system to the learner: that each digit's pronunciation is introduced at first appearance, and that teens and multiples of ten are single words, not digit-by-digit composites. This note appears on the first numeral only.

---

## Variant entries

Use `"type": "variant"` entries for literary or archaic forms that are not a citation-form lemma — e.g. `گفتا` (archaic narrative past of `گفتن`), `سرورا` (vocative of `سرور`). Set `meaning` to a Markdown string that identifies the base form and, where a grammar note explains the construction, includes a Markdown hyperlink to it. Example:

```json
"meaning": "vocative of `سرور`; see [Grammar: Archaic register](#grammar-archaic-register)"
```

---

## Etymology (`etym`)

Add an `etym` object **only when the answer is interesting**:

- **Arabic loanwords** (common in religious/literary register): set `prose` to note the source language and triliteral root (e.g. `"from Arabic, root r-ḥ-m \"compassion\""`). Also set `arabic_form` to a value matching one of the form sections in `study_guide/arabic.md` — the renderer turns it into a link to that section on `../arabic.html`. The valid values are defined in `_ARABIC_FORM_ANCHORS` in `render_json.py`. If the form you need has no section yet on the Arabic reference page, add one to `study_guide/arabic.md` and a corresponding entry to `_ARABIC_FORM_ANCHORS`. When `root` is set, also set `arabic_form` (the renderer warns if `root` is present without `arabic_form`).
- **Compounds with meaningful morphemes**: break down the parts in `prose`. Example: `` "`سر` sar \"head\" + `گذشت` gozašt \"past\" (← `گذشتن` \"to pass\")" ``. Hyperlink any affixes to `word_formation.html` as described in the cross-linking rule below.
- **Proper nouns of foreign origin**: Hebrew (most BoM names via Arabic or English transliteration) or English.
- **Classical Persian etymologies** (tracing a native word back to Middle Persian, Old Persian, Avestan, or Proto-Iranian) are welcome when the history is interesting.
- **Ordinary native Persian words** with no notable history — don't add `etym`.

**Morpheme-breakdown notation** inside `prose` strings: wrap every Persian fragment in backticks. Use `→` to spell out the compositional meaning; use `←` to trace a form back to its source verb or root.

**Cross-linking affixes to `word_formation.html`.** Whenever an affix mentioned in `etym.prose`, `family`, or a `forms[].desc` is covered by `study_guide/word_formation.md`, make the affix text a Markdown link to the relevant anchor on `../word_formation.html`. Example: `` [`-ی`](../word_formation.html#the-abstract-noun-suffix-g) ``. Do **not** link ezafe (`-e`), the object marker (`-rā`), the plural suffix (`-hā`), the comparative (`-tar`), or possessive clitics — these are too ubiquitous to warrant per-link treatment. If an affix seems worth linking but isn't yet documented in `word_formation.md`, ask the user whether to add it before proceeding.

---

## Word family (`family`)

Set the `family` field (a Markdown string) when:

- The entry's stem is a useful Persian word in its own right that doesn't otherwise appear in the chapter.
- The entry has derivational siblings the reader will meet later.
- A compound's components are themselves vocabulary worth memorizing.
- A related form is superficially similar to an unrelated word — add a parenthetical disambiguation.

**Format**: short list, each related form with its translit and a one-or-two-word gloss, separated by `;`. Don't repeat the entry's headword; don't repeat detail already in `etym`.

---

## Forms array (`forms`)

The `forms` array serves two purposes that can be combined freely within the same entry.

**Purpose 1 — Token registration.** Every surface form of any lemma (verb, noun, adjective, …) that appears in the chapter's source text and cannot be auto-resolved to the headword needs a `forms` entry with an `fa` field. See [Token registration rules](#token-registration-rules) below.

**Purpose 2 — Explanatory content.** Some forms are worth documenting even if they don't appear in this chapter:
- **Verb paradigm information worth flagging for learners:**
  - Suppletive present stems: `دیدن` (pres. `bīn-`), `آمدن` (pres. `ā-`), `دادن` (pres. `deh-`), `رفتن` (pres. `rav-`).
  - Conjugation quirks: `داشتن` drops `می-` in the present indicative (`دارد`, never `می‌دارد`); prefixed compounds of `داشتن` reverse this (`برمی دارد`). Compound-verb subjunctives routinely drop `بـ-` (`توانا سازد`).
  - Auxiliary uses: `خواستن` as future auxiliary; `شدن` as passive auxiliary.
  - High-frequency verbs in many shapes (`بودن`, `شدن`, `کردن`, `داشتن`, `دادن`): summarize the paradigm visible in this chapter.
- **Common collocations or related compound forms** of any lemma — put these in `forms` rather than embedding them in `meaning`.
- **Source-text orthography that differs from the headword citation form** — e.g. when the Book of Mormon text writes a word with diacritics not reflected in the `persian` field.

Each item in `forms` is one of:

- `{"fa": "surface form", "desc": "description"}` — a registerable surface form; `fa` is the token-lookup key; `desc` is a Markdown string. Inside `desc`, cite verbatim Persian from the source text with a section reference: e.g. `"3sg pres. \`می آید\` _mī-āyad_ ([verse 9](#verse-9))"`. A single item may stack several related forms in `desc` separated by semicolons (present → past → pp).

- `{"note": "prose note"}` — a prose remark with no token registration. Use this for content that doesn't correspond to a specific surface form: paradigm summaries (`"present indicative drops می-, so دارد not *می‌دارد"`), conjugation quirks that apply across forms, cross-references to grammar notes, or meta-information about the lemma. Example: `{"note": "bare پیش without a preposition is archaic; modern usage prefers قبل از"}`.

### Token registration rules

The renderer tokenizes source text on whitespace and links each token to a vocab entry. A token is linked if it:

(a) exactly matches a headword `persian` value,
(b) matches after stripping harakat diacritics (U+0610–U+061A, U+064B–U+065F) — **not** `ۀ` (U+06C0), or
(c) matches the `fa` value of any item in any headword's `forms` array.

The following surface forms require **explicit `forms` entries** because they are not auto-resolved:

- **Ezafe forms ending in `ۀ`** — `کرانۀ`, `همۀ`, `پایۀ`, `نگاشتۀ` etc. Add: `{"fa": "همۀ", "desc": "ezafe form _hame-ye_"}`.
- **Fused possessive/clitic forms** — `گرانبهایش`, `کتابم` etc. Add them explicitly when they appear in source tokens.
- **Negative verb forms** — `نداشتند`, `نبرد` etc. are not auto-derived from the positive form.
- **Comparative suffix `-تر`** — `نزدیکتر`, `بیشتر` etc. are not auto-resolved from the adjective.
- **Subjunctive 3pl `-اند`** forms (e.g. `شوند`, `بدانند`).
- **Multi-word compound verb forms** — `{"fa": "می گوید", ...}` registers the two-token phrase as a bigram; it does not register `گوید` alone. Add a separate `{"fa": "گوید", ...}` item if the bare verb appears as a standalone source token.

**Multi-word (bigram) linking.** This is not related to the می/نمی prefix — those are combined with the following verb token automatically by the renderer without any `forms` entries. Bigrams are for compound verbs and fixed phrases whose two tokens appear as separate whitespace-delimited words but should link together to a single headword. For example, if the source text contains `نگه دارند` and the headword is `نگه داشتن`, add `{"fa": "نگه دارند", "desc": "..."}` — the renderer will wrap both tokens in one link. A `forms` item with a space in `fa` registers as a bigram; when both tokens appear consecutively in source text, they are wrapped in a single link. Bigrams take priority over single-token matches.

**Unlinked-word warnings.** After running the renderer, it prints `unlinked:` warnings to stderr for source-text tokens it could not map, with a count and section name. Treat every warning as a missing `forms` entry or missing headword.

---

## Reading warnings (`warning`)

Set the `warning` field (a Markdown string) on a headword entry whenever the written form of a word does not match what a learner applying standard Persian spelling rules would expect — regardless of whether the word is Arabic, Persian, or anything else. The renderer displays it as a ⚠️ note before the `etym` line.

Rules:
- Use the `warning` field — not `meaning` or a `forms` note.
- Name the specific phenomenon in italic. One sentence; end with `Learners may accidentally read it as \*_wrongform_.` (single preceding asterisk is the standard linguistic convention for an ungrammatical/incorrect form; the romanization is italicised like all other transliterations).
- Persian in backticks; transcriptions in italic underscores.

Common categories:

| Phenomenon | When to use |
|---|---|
| `Alif maqṣūra` | Arabic final ى — written ی in Persian — is read -ā, not -ī (e.g. `حتّی` _ḥattā_ "even"). |
| `Diphthong -ay- written as ی` | Arabic _-ay-_ diphthong where learners expect Persian long _-ī-_ (e.g. `علیه` _ʿalayhi_ "against"). |
| Silent letter / historical spelling | A letter present in the written form that is not pronounced (e.g. the و in `خواهر` _xāhar_ "sister"). |

---

## Grammar notes

Grammar note entries have `"type": "grammar-note"` and live in the `entries` array of the study section where the relevant construction first appears. Fields:

| Field | Description |
|---|---|
| `title` | Short descriptive title; also the HTML anchor (slugified). Example: `"Grammar: Subjunctive after تا"` |
| `body` | Markdown prose explaining the grammar point (1–3 paragraphs) |
| `examples` | Array of example objects — each must be taken **verbatim from this chapter's source text** |
| `closing` | Optional Markdown prose after the last example |

Each item in `examples`:

| Field | Description |
|---|---|
| `ref` | Display label, e.g. `"Verse 9"`, `"Chapter summary"` |
| `ref_anchor` | Anchor for the link, e.g. `"verse-9"`, `"chapter-summary"` |
| `persian` | Persian text; use `{e}` to mark editorial ezafe in prose strings |
| `translit` | Romanization |
| `en` | English translation (optional) |

Grammar notes do not get a separate top-level section — they are entries woven into the vocab list at the point where the construction first occurs.

**Standing list of points worth covering when they appear in a chapter:**

- `چنین گذشت` — the "and it came to pass" calque
- Passive voice with `شدن` (past participle + شدن)
- Future tense `خواه- + short infinitive`
- Subjunctive after `تا`
- Ezafe chains
- Indefinite marker `-ī` on nouns
- Direct-object marker `را` and its position after a noun phrase
- Compound verbs (noun/adjective + `کردن` / `شدن`)
- Possessive / pronominal suffixes `-am -at -aš -mān -tān -šān`
- Archaic / biblical register: `گفتا` narrative `-ā`, `آری`, `بنگرید`, `سرور` for "the Lord", bookish verbs like `نگاشتن`, `نیایش کردن`, `بانگ برآوردن`
- Relative clauses with `که`
- Imperfective `می-` and its negation `نمی-`

Cover only points the chapter actually contains.

---

## Reading tips section

Set the `reading_tip` field at the top level of `study.json`. It is rendered immediately after the intro, before the vocabulary. Write one short paragraph naming the key grammar constructions the reader will encounter in the chapter, followed by one practical study-tip sentence (e.g. "Pay particular attention to ezafe chains — nearly every noun phrase in this chapter uses them").

**Language: English.** Like `intro`, `reading_tip` is study-aid prose for the learner and must be written in English.

---

## Editorial ezafe

The Persian BoM source rarely writes the unstressed ezafe linker (`-e` / `-ye`) on consonant-final words. Mark editorial ezafe explicitly:

- In **`source.json` tokens**: set `"e": true` on the token where ezafe follows.
- In **grammar-note prose fields** (`body`, `closing`) and **example `persian` strings**: write `{e}` after the word (e.g. `"رحمت‌های مهرآمیز{e} سرور"`). The renderer converts `{e}` to a styled kasra span.

**Mark ezafe when** it is unwritten in the publisher's source text.

**Do not mark ezafe when** it is already visible in the spelling:
- `ۀ` on words ending in silent `ه` (e.g. `نگاشتۀ`, `همۀ`) — publisher already wrote it.
- `ی` on words ending in long `ا` / `و` (e.g. `خدای قادر`, `روی زمین`).
- `های` (plural + ezafe) on plural-marked nouns (e.g. `رحمت‌های مهرآمیز`).
- An explicit kasra the publisher wrote in the original (e.g. `کتابِ نبوّت`). Leave it unstyled.

---

## Interlinear gloss format

Each token in `source.json` may carry a `gloss` sub-object with `src` (romanized transliteration with morphological boundaries) and `gloss` (Leipzig gloss label):

```json
{"fa": "همسرش", "gloss": {"src": "hamsar-aš", "gloss": "wife-3SG.POSS"}}
```

Abbreviations follow [Leipzig Glossing Rules](https://www.eva.mpg.de/lingua/resources/glossing-rules.php). Lexical content lowercase; grammatical abbreviations UPPERCASE; multi-part labels joined with `.`; morpheme boundaries with `-`; clitic boundaries with `=`. Person and number written together: `1SG`, `2PL`, `3SG`, `3PL`.

**Standard abbreviations:**

| Abbrev | Meaning | `src` / `gloss` example |
|--------|---------|---------|
| `ACC` | accusative (`را`) | `"rā"` / `"ACC"` |
| `CL` | classifier / counter | `"tā=ye"` / `"CL=EZ"` |
| `COMP` | complementizer `که` (clause) | `"ke"` / `"COMP"` |
| `COP` | copula (`است`, enclitic) | `"ast"` / `"COP-3SG"` |
| `EZ` | ezafe linker | `"ketāb=e"` / `"book=EZ"` |
| `FUT` | future auxiliary (`خواه-`) | `"xāh-am"` / `"FUT-1SG"` |
| `IMPF` | imperfective prefix (`می-`) | `"mī"` / `"IMPF"` |
| `INDEF` | indefinite suffix (`-ī`) | `"ketāb-ī"` / `"book-INDEF"` |
| `INF.PST` | past-stem infinitive (future constructions) | `"negāšt"` / `"write-INF.PST"` |
| `NEG` | negative prefix | `"na-xāh-am"` / `"NEG-FUT-1SG"` |
| `NARR` | narrative suffix (`-ā` on گفتا) | `"goft-ā"` / `"say-NARR"` |
| `PASS` | passive (pp + شدن) | `"šav-ad"` / `"become-PASS-3SG"` |
| `PL` | plural (`-hā`) | `"hā=ye"` / `"PL=EZ"` |
| `POSS` | possessive enclitic | `"hamsar-aš"` / `"wife-3SG.POSS"` |
| `PRS` | present tense | `"kon-ad"` / `"do-PRS-3SG"` |
| `PRV` | preverb (separable prefix) | `"bar-mī"` / `"PRV=IMPF"` |
| `PST` | past tense | `"kard"` / `"do-PST-3SG"` |
| `PTCP` | participle | `"xānde"` / `"call-PTCP.PST"` |
| `REL` | relative particle `که` | `"ke"` / `"REL"` |
| `SBJV` | subjunctive | `"šav-and"` / `"become-SBJV-3PL"` |
| `SG` | singular | used in person+number combos: `1SG`, `3SG` |
| `VOC` | vocative | `"Sarvar-ā"` / `"Lord-VOC"` |

**Persian numerals.** Use the spelled-out transliteration as `src`: `"yek"` / `"1"`, `"do"` / `"2"`, etc. For larger heading numbers (e.g. 600 B.C.): `"src": "600", "gloss": "600"`.

**`می`/`نمی` tokens.** The publisher writes the imperfective prefix with a space before the verb stem, so each is a separate token in the `tokens` array with its own `gloss` sub-object: `{"fa": "می", "gloss": {"src": "mī", "gloss": "IMPF"}}`. In `forms` items, write them together in one `fa` value: `"می دهد"` (not two separate items).

**Source slot boundaries.** Use `-` for bound morphemes (`hamsar-aš`, `šod-and`); use `=` for clitics (`ketāb=e`, `sarzamīn=e`). Ezafe is always a clitic (`=EZ`). Boundaries in `src` must match the segmentation in `gloss`.

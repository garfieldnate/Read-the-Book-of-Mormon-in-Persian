- whole-book word index
- mark site as ai-generated, not human-checked; add paragraph in main index
- Review all study guide construction rules in readme. Don't want/need a chapter summary/intro in English, for example.
- tag words by language of origin (native Persian, Arabic borrowing, Turkish, other borrowing). Use it to make an index by language of origin, and maybe also to nicely format a visual tag for the language of origin in vocab entries.
- Add readme instructions to break down the work of a new chapter to avoid huge API return values.
- Link to alif maqsura section in reference from study guide when they occur
- Noun derivation page for native Persian words (e.g., `-i` for adjectives, `-gāh` for places, etc.)
    - https://en.wikipedia.org/wiki/Persian_vocabulary
	- https://en.wikipedia.org/wiki/Persian_nouns
- Mention causative infix on verb page (though it's not completely productive)
- Index for Arabic borrowings using JSON root info (all words with same root in a section)
- Nail down styling guide for mixed LTR/RTL
- Generate exercises
- Break up BoM study with some real-life usage info, maybe church themed to keep it on theme
- Reference page on pronouns, including demonstratives and interrogatives, clitics

New instructions file for chapter generation:
* Download source text
* Generate source file (parsed, tokenized, glossed)
* List out unique lemma in the source and their first uses, plus all other occurrences by form.
* Use that list to generate vocab entries, with lemmas listed as vocab headwords and forms listed in `*Forms*` with verse citations, plus all the other enriching info.
    * do this job one source section at a time so we can watch progress.

* Lint scripts needed:
    * ensure all forms are listed in a vocab entry.

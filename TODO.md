- lots of cleanups, styling on Arabic borrowings page
- collapse vocab sections so you can read straight through
- whole-book word index
- mark site as ai-generated, not human-checked; add paragraph in main index
- Review all study guide construction rules in readme. Don't want/need a chapter summary/intro in English, for example.
- Add readme instructions to break down the work of a new chapter to avoid huge API return values.
- Persian alphabet page (also mention Alif maqsura, and how Arabic text can be quickly differentiated by looking for a ye with two dots below it word-finally, which Persian doesn't have).
- Page on Persian plurals
- Noun derivation page for native Persian words (e.g., `-i` for adjectives, `-gāh` for places, etc.)
    - https://en.wikipedia.org/wiki/Persian_vocabulary
	- https://en.wikipedia.org/wiki/Persian_nouns
- Mention causative infix on verb page (though it's not completely productive)
- Index for Arabic borrowings using JSON root info (all words with same root in a section)

New instructions file for chapter generation:
* Download source text
* Generate source file (parsed, tokenized, glossed)
* List out unique lemma in the source and their first uses, plus all other occurrences by form.
* Use that list to generate vocab entries, with lemmas listed as vocab headwords and forms listed in `*Forms*` with verse citations, plus all the other enriching info.
    * do this job one source section at a time so we can watch progress.

* Lint scripts needed:
    * ensure all forms are listed in a vocab entry.

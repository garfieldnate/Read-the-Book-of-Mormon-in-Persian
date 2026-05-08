- lots of cleanups, styling on Arabic borrowings page
- collapse vocab sections so you can read straight through
- whole-book word index
- mark site as ai-generated, not human-checked; add paragraph in main index
- Move translit stuff out of readme; just reference translit page instead.
- Review all study guide construction rules in readme. Don't want/need a chapter summary/intro in English, for example.
- Add readme instructions to break down the work of a new chapter to avoid huge API return values.
- Persian alphabet page (also mention Alif maqsura, and how Arabic text can be quickly differentiated by looking for a ye with two dots below it word-finally, which Persian doesn't have).
- Page on Persian plurals
- Noun derivation page for native Persian words (e.g., `-i` for adjectives, `-gāh` for places, etc.)
    - https://en.wikipedia.org/wiki/Persian_vocabulary
	- https://en.wikipedia.org/wiki/Persian_nouns
- Mention causative infix on verb page (though it's not completely productive)


Instructions:
* Iterate to ensure everything is linked
* Need a script to ensure all forms are listed in a vocab entry.
* Separate out data from presentation; put sections and sentences in one file, vocab and grammar entries in another file, and have a script stitch them together. This will make it easier to edit the data without worrying about formatting.
* Ensure there's a number entry for every verse number
* Arabic etymologies link to forms
* Script to check JSON against schemata
* Step 1 for new page will be downloading source, separating by sentence, separating by word, generating lemmas, then probably doing grammar and then vocab.

* Make sure JSON schema are well-documented.

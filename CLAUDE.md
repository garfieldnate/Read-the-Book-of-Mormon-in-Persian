# CLAUDE.md

## Generated files

The `.md` files inside `study_guide/01_nephi/` (e.g. `ch1.md`, `ch2.md`) are **generated output** — do not edit them directly. Always edit the corresponding JSON source files:

- `chN.study.json` — vocabulary, grammar notes, forms, verse glosses
- `chN.source.json` — source text / verse data

Run `render_json.py` (or `build_site.py`) to regenerate the markdown after editing JSON.

The reference pages in `study_guide/` (`verbs.md`, `word_formation.md`, etc.) are hand-authored and can be edited directly.

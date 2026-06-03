# CLAUDE.md

## Source files and generated output

Chapter study guides live as JSON source files — do not author or edit Markdown for them:

- `chN.study.json` — vocabulary, grammar notes, forms, verse glosses
- `chN.source.json` — source text / verse data

Run `render_json.py` (or `build_site.py`) to regenerate the HTML after editing JSON.

The reference pages in `study_guide/` (`verbs.md`, `word_formation.md`, etc.) are hand-authored Markdown and can be edited directly.

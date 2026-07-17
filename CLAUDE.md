# CLAUDE.md

## Source files and generated output

Chapter study guides live as JSON source files — do not author or edit Markdown for them:

- `chN.study.json` — vocabulary, grammar notes, forms, verse glosses
- `chN.source.json` — source text / verse data

Run `render_json.py` (or `build_site.py`) to regenerate the HTML after editing JSON.

To generate a new chapter from scratch, follow **[GENERATING_CHAPTERS.md](GENERATING_CHAPTERS.md)**.

The reference pages in `study_guide/` (`verbs.md`, `word_formation.md`, etc.) are hand-authored Markdown and can be edited directly.

## Audio (text-to-speech)

Per-section audio players are generated at build time by `generate_audio.py` and committed under `study_guide/audio/<book>/<chap>/`. Regenerating audio needs the ElevenLabs key in `.env` (`11labsApiKey`), a **paid** ElevenLabs plan (the chosen voices are library voices — free tier gives HTTP 402), and `ffmpeg`. The site build itself needs no key. Text-builder rules (verse-number handling, ezafe) live in `tts_text.py`; runtime player logic in `study_guide/player.js`. See the **Audio** section of `README.md` and Step 5 of `GENERATING_CHAPTERS.md`.

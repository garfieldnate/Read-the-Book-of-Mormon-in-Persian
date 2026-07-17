"""Build the exact Persian string sent to the TTS engine from a section's tokens.

This lives apart from ``render_json`` so the audio generator and the HTML
renderer agree byte-for-byte on the text that was spoken. The character offsets
returned here are what let us fold the engine's character-level timestamps back
onto individual tokens (and therefore onto the rendered word ``<a>`` elements).

The spacing rules mirror ``render_json._render_tokens`` exactly:
  * a word token is preceded by a space iff the previous token was a "word"
    (a ``fa`` token, or clause/sentence-ending punctuation);
  * punctuation is appended with no leading space.

Editorial ezafe (``"e": true``) is normally NOT written in Persian, so it is
omitted by default. ``include_ezafe=True`` appends a kasre to the host word —
kept as a one-line lever so the spike can A/B whether v3 needs the hint.
"""

# Kasre ( زیر) — the editorial ezafe vowel mark.
KASRE = "ِ"

# Punctuation after which the next word takes a leading space. Mirrors the set
# in render_json._render_tokens so text and rendering stay aligned.
_SPACE_AFTER_PUNCT = frozenset({".", "،", "؛", ":", "!", "؟", "?"})

# Digit characters that can make up a standalone verse number: Persian,
# Arabic-Indic, and ASCII.
_DIGITS = frozenset("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩0123456789")


def _is_number(fa: str) -> bool:
    return bool(fa) and all(c in _DIGITS for c in fa)


def build_tts_text(
    tokens: list[dict],
    include_ezafe: bool = False,
    number_sep: str | None = ". ",
) -> tuple[str, list[tuple[int, int, int]]]:
    """Return ``(text, spans)`` for a section's token list.

    ``spans`` has one ``(token_index, char_start, char_end)`` entry per token
    that contributes characters, where ``text[char_start:char_end]`` is that
    token's own glyphs (joining spaces belong to no span). Tokens with neither
    ``fa`` nor ``p`` contribute nothing and produce no span.

    ``number_sep`` controls a leading digit-only token (a verse number). The
    number should be spoken, but set apart so the engine doesn't fold it into
    the first phrase — so ``number_sep`` (e.g. ``". "``) is inserted after it as
    joining text (no span of its own). Set ``number_sep=None`` to omit the verse
    number from the audio entirely. Mid-text numbers are unaffected.
    """
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    pos = 0
    prev_was_word = False
    seen_word = False

    for idx, tok in enumerate(tokens):
        if "fa" in tok:
            leading_number = not seen_word and _is_number(tok["fa"])
            seen_word = True
            if leading_number and number_sep is None:
                continue  # verse number not spoken
            if prev_was_word:
                parts.append(" ")
                pos += 1
            piece = tok["fa"]
            if include_ezafe and tok.get("e"):
                piece += KASRE
            start = pos
            parts.append(piece)
            pos += len(piece)
            spans.append((idx, start, pos))
            if leading_number:
                # set the number apart with a separator (belongs to no span);
                # it already ends in a space, so the next word adds none.
                parts.append(number_sep)
                pos += len(number_sep)
                prev_was_word = False
            else:
                prev_was_word = True
        elif "p" in tok:
            piece = tok["p"]
            start = pos
            parts.append(piece)
            pos += len(piece)
            spans.append((idx, start, pos))
            prev_was_word = piece in _SPACE_AFTER_PUNCT

    return "".join(parts), spans


def fold_char_times(
    spans: list[tuple[int, int, int]],
    characters: list[str],
    start_times: list[float],
    end_times: list[float],
) -> dict[int, list[float]]:
    """Fold character-level timestamps onto tokens.

    Given the engine's per-character ``characters`` / ``start_times`` /
    ``end_times`` arrays (which align 1:1 with the text passed to
    ``build_tts_text``) return ``{token_index: [t0, t1]}`` where ``t0`` is the
    earliest character start and ``t1`` the latest character end within the
    token's char range. Tokens whose glyphs carry no timing (shouldn't happen)
    are skipped.
    """
    n = min(len(characters), len(start_times), len(end_times))
    out: dict[int, list[float]] = {}
    for idx, cs, ce in spans:
        lo = max(cs, 0)
        hi = min(ce, n)
        if hi <= lo:
            continue
        t0 = min(start_times[lo:hi])
        t1 = max(end_times[lo:hi])
        out[idx] = [round(t0, 3), round(t1, 3)]
    return out

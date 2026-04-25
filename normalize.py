#!/usr/bin/env python3
"""Normalize PDF-extraction corruption in Persian Book of Mormon text.

The source PDF was extracted with a converter that mis-orders characters
inside certain ligature combinations: specific bigrams swap (e.g. رشوع for
شروع), and at least one token (سرور, "Lord") loses a ر entirely. The fix
is a maintained lookup table of {corrupt_form: correct_form} word pairs in
corruptions.json, applied as whole-word replacements so legitimate
substrings are not clobbered.

Usage:
    python3 normalize.py <input.txt> <output.txt>

Reads corruptions.json from the same directory as this script.
Prints a summary of replacements to stderr.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

PUNCT = '،؛؟٬٫:!.?,;"\'()[]{}«»“”‘’—–-…'


def strip_punct(tok: str) -> tuple[str, str, str]:
    leading = ""
    while tok and tok[0] in PUNCT:
        leading += tok[0]
        tok = tok[1:]
    trailing = ""
    while tok and tok[-1] in PUNCT:
        trailing = tok[-1] + trailing
        tok = tok[:-1]
    return leading, tok, trailing


def normalize(text: str, corruptions: dict[str, str]) -> tuple[str, Counter]:
    counts: Counter = Counter()
    out: list[str] = []
    for chunk in re.split(r"(\s+)", text):
        if not chunk or chunk.isspace():
            out.append(chunk)
            continue
        leading, core, trailing = strip_punct(chunk)
        if core in corruptions:
            counts[core] += 1
            core = corruptions[core]
        out.append(leading + core + trailing)
    return "".join(out), counts


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <input.txt> <output.txt>", file=sys.stderr)
        return 2
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    script_dir = Path(__file__).resolve().parent
    corruptions = json.loads((script_dir / "corruptions.json").read_text(encoding="utf-8"))
    text = in_path.read_text(encoding="utf-8")
    fixed, counts = normalize(text, corruptions)
    out_path.write_text(fixed, encoding="utf-8")
    total = sum(counts.values())
    print(
        f"applied {total} replacement(s) across {len(counts)} distinct corrupt token(s):",
        file=sys.stderr,
    )
    for tok, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {n:3d}x  {tok} → {corruptions[tok]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate TTS audio + word-level timings + waveform peaks for source sections.

Uses the ElevenLabs text-to-speech ``/with-timestamps`` endpoint (model
``eleven_v3`` — the only model that speaks Persian). One call returns the mp3
plus character-level timings, which we fold onto tokens so the player can
highlight and click-to-play individual words. Waveform peaks are precomputed
with ffmpeg so pages render the waveform without downloading/decoding audio.

Voices are assigned by section role, mirroring the English recording:
  verses -> IMan (male, Persian-native);  summaries -> Zara (female).
Pass ``--voice`` to override with one voice for all sections (A/B testing).

The API key is read from ``.env`` (key name: ``11labsApiKey``).

Generate a whole chapter (role voices, per-chapter output dir):
    python generate_audio.py --source study_guide/01_nephi/ch1.source.json

Preview text + character cost without spending credits:
    python generate_audio.py --source study_guide/01_nephi/ch1.source.json --dry-run
"""
from __future__ import annotations

import argparse
import array
import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from tts_text import build_tts_text, fold_char_times

ROOT = Path(__file__).resolve().parent
API = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_v3"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"

# Friendly names for the separator inserted after a spoken verse number.
NUMBER_SEPS = {"period": ". ", "comma": "، ", "dash": " — ", "none": None}

# Voice per section role (verse vs summary), mirroring the English BoM recording.
ROLE_VOICES = {
    "verse":   ("3AA408tBxTzz5dPx3TsR", "IMan"),   # male — verses / main source text
    "summary": ("jqcCZkN6Knx8BJ5TBdYR", "Zara"),   # female — chapter & book summaries
}
PEAK_BUCKETS = 480


# ---------- config / http ----------

def load_api_key() -> str:
    env = ROOT / ".env"
    if not env.exists():
        sys.exit("error: .env not found (expected key 11labsApiKey)")
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() == "11labsApiKey":
            return val.strip().strip('"').strip("'")
    sys.exit("error: 11labsApiKey not found in .env")


def load_overrides() -> dict[str, str]:
    """Load {fa: spoken_form} pronunciation overrides from pronunciations.json.

    Each entry maps a Persian surface form to a corrected spoken form (a harakat
    respelling under the ``say`` key). Missing file -> no overrides.
    """
    path = ROOT / "pronunciations.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {fa: e["say"] for fa, e in data.items() if isinstance(e, dict) and e.get("say")}


def _request(method: str, url: str, key: str, data: dict | None = None) -> dict:
    headers = {"xi-api-key": key}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(
            f"error: HTTP {e.code} from {method} {url}\n{detail}\n"
            "(402 = the voice needs a paid plan; 401 = the key is missing a "
            "permission or the model isn't enabled for your tier.)"
        )
    except urllib.error.URLError as e:
        sys.exit(f"error: could not reach {url}: {e.reason}")


# ---------- section handling ----------

def section_anchor(sec: dict) -> str:
    """Stable per-section id, matching render_json._section_heading."""
    t = sec.get("type") or sec.get("section_type", "")
    n = sec.get("number")
    fixed = {
        "chapter-summary": "chapter-summary",
        "book-summary-title": "title",
        "book-summary-subtitle": "subtitle",
    }
    if t in fixed:
        return fixed[t]
    if t == "verse":
        return f"verse-{n}"
    if t == "book-summary-sentence":
        return f"sentence-{n}"
    return t


def section_role(sec: dict) -> str:
    """'verse' for main source text, 'summary' for chapter/book summaries."""
    t = sec.get("type") or sec.get("section_type", "")
    return "verse" if t == "verse" else "summary"


# ---------- audio processing ----------

def compute_peaks(mp3: bytes, buckets: int = PEAK_BUCKETS) -> tuple[list[float] | None, float | None]:
    """Decode mp3 via ffmpeg → (per-bucket normalized peak amplitudes, duration).

    Returns (None, None) if ffmpeg is unavailable so callers can degrade to
    client-side decoding.
    """
    try:
        proc = subprocess.run(
            ["ffmpeg", "-v", "quiet", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "8000", "pipe:1"],
            input=mp3, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None
    pcm = array.array("h")
    pcm.frombytes(proc.stdout)
    n = len(pcm)
    if not n:
        return [], 0.0
    duration = n / 8000.0
    step = max(1, -(-n // buckets))  # ceil division
    peaks = [round(max(abs(x) for x in pcm[i:i + step]) / 32768, 4) for i in range(0, n, step)]
    return peaks, round(duration, 3)


# ---------- synthesis + output ----------

def synthesize(
    tokens: list[dict],
    include_ezafe: bool,
    voice_id: str,
    model: str,
    key: str,
    number_sep: str | None,
    overrides: dict[str, str] | None = None,
) -> tuple[bytes, dict[int, list[float]], str, float]:
    """Return (mp3_bytes, token_times, text, token_duration)."""
    text, spans = build_tts_text(tokens, include_ezafe, number_sep=number_sep, overrides=overrides)
    url = f"{API}/text-to-speech/{voice_id}/with-timestamps?output_format={DEFAULT_OUTPUT_FORMAT}"
    resp = _request("POST", url, key, {"text": text, "model_id": model})
    audio = base64.b64decode(resp["audio_base64"])
    al = resp.get("alignment") or {}
    token_times = fold_char_times(
        spans,
        al.get("characters", []),
        al.get("character_start_times_seconds", []),
        al.get("character_end_times_seconds", []),
    )
    token_duration = max((t[1] for t in token_times.values()), default=0.0)
    return audio, token_times, text, token_duration


def write_outputs(
    out_dir: Path,
    name: str,
    audio: bytes,
    token_times: dict[int, list[float]],
    text: str,
    meta: dict,
    token_duration: float,
) -> float:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.mp3").write_bytes(audio)

    peaks, peak_duration = compute_peaks(audio)
    duration = round(peak_duration if peak_duration else token_duration, 3)

    # Build-time sidecar: token → [t0, t1], read by render_json to stamp words.
    (out_dir / f"{name}.timing.json").write_text(
        json.dumps(
            {**meta, "text": text, "duration": duration,
             "tokens": {str(k): v for k, v in sorted(token_times.items())}},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    # Runtime sidecar: waveform peaks, fetched by player.js.
    if peaks is not None:
        (out_dir / f"{name}.peaks.json").write_text(
            json.dumps({"version": 1, "duration": duration, "peaks": peaks}, ensure_ascii=False),
            encoding="utf-8",
        )
    return duration


def default_out_dir(source_path: Path) -> Path:
    """study_guide/<book>/chN.source.json  ->  study_guide/audio/<book>/chN"""
    book_dir = source_path.parent.name
    chap = source_path.name.split(".")[0]
    return ROOT / "study_guide" / "audio" / book_dir / chap


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="path to a chN.source.json")
    ap.add_argument("--section", help="only this section anchor (e.g. verse-1)")
    ap.add_argument("--voice", help="override: one voice_id for all sections (default: by role)")
    ap.add_argument("--tag", default="", help="label inserted into filename: {anchor}.{tag}[.ezafe]")
    ap.add_argument("--ab", action="store_true", help="emit both ezafe and no-ezafe variants")
    ap.add_argument("--ezafe", action="store_true", help="include editorial ezafe (kasre) in the text")
    ap.add_argument("--number-sep", default="period", choices=list(NUMBER_SEPS),
                    help="separator after a spoken verse number (default: period); 'none' omits it")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"model_id (default: {DEFAULT_MODEL})")
    ap.add_argument("--out", help="output dir (default: study_guide/audio/<book>/<chap>)")
    ap.add_argument("--force", action="store_true", help="regenerate even if outputs already exist")
    ap.add_argument("--dry-run", action="store_true", help="print text + char cost, no API calls")
    args = ap.parse_args()

    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = (ROOT / args.source).resolve()
    if not source_path.exists():
        sys.exit(f"error: {source_path} not found")
    data = json.loads(source_path.read_text(encoding="utf-8"))

    targets = [s for s in data.get("sections") or [] if s.get("tokens")]
    if args.section:
        targets = [s for s in targets if section_anchor(s) == args.section]
        if not targets:
            sys.exit(f"error: no section with anchor {args.section!r} in {source_path.name}")

    variants = [("", False), (".ezafe", True)] if args.ab else [("", args.ezafe)]
    number_sep = NUMBER_SEPS[args.number_sep]
    overrides = load_overrides()
    out_dir = Path(args.out).resolve() if args.out else default_out_dir(source_path)
    tag = f".{args.tag}" if args.tag else ""

    if args.dry_run:
        total = 0
        for sec in targets:
            anchor = section_anchor(sec)
            role = section_role(sec)
            _, vname = (args.voice, "(override)") if args.voice else ROLE_VOICES[role]
            for suffix, ez in variants:
                text, _spans = build_tts_text(sec["tokens"], ez, number_sep=number_sep, overrides=overrides)
                total += len(text)
                print(f"[{anchor}{tag}{suffix}] {len(text)} chars  voice={vname}")
                print(f"    {text}")
        print(f"\nTotal: {total} characters (~{total} credits on v3 @ 1 credit/char)")
        print(f"Output dir: {out_dir}")
        return 0

    key = load_api_key()
    print(f"Model: {args.model}   Output: {out_dir.relative_to(ROOT) if out_dir.is_relative_to(ROOT) else out_dir}\n")

    for sec in targets:
        anchor = section_anchor(sec)
        role = section_role(sec)
        voice_id, vname = (args.voice, "(override)") if args.voice else ROLE_VOICES[role]
        for suffix, ez in variants:
            name = f"{anchor}{tag}{suffix}"
            timing_path = out_dir / f"{name}.timing.json"
            want_text, _ = build_tts_text(sec["tokens"], ez, number_sep=number_sep, overrides=overrides)
            # Text-aware cache: regenerate only when the spoken text changed
            # (new section, edited tokens, or a new pronunciation override).
            if not args.force and timing_path.exists():
                try:
                    if json.loads(timing_path.read_text(encoding="utf-8")).get("text") == want_text:
                        print(f"[{name}] up to date, skipping")
                        continue
                except (ValueError, OSError):
                    pass
            print(f"[{name}] synthesizing with {vname}...")
            audio, token_times, text, token_dur = synthesize(
                sec["tokens"], ez, voice_id, args.model, key, number_sep, overrides
            )
            meta = {
                "anchor": anchor, "role": role, "model": args.model,
                "voice_id": voice_id, "voice_name": vname,
                "include_ezafe": ez, "number_sep": args.number_sep,
            }
            dur = write_outputs(out_dir, name, audio, token_times, text, meta, token_dur)
            print(f"    -> {name}.mp3 ({dur:.1f}s)  {len(token_times)} words timed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

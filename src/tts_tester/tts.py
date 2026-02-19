"""Thin wrapper around the Google Cloud Text-to-Speech API."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from google.cloud import texttospeech as tts

from tts_tester.config import TTSConfig

_OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"


# ── Voice listing ────────────────────────────────────────────────────────────


def list_voices(
    language_code: str | None = None,
    name_contains: str | None = None,
    gender: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch voices from the API and optionally filter them.

    Returns a list of dicts with keys:
        name, language_codes, ssml_gender, natural_sample_rate_hertz
    """
    client = _get_client()
    resp = client.list_voices(language_code=language_code or "")
    gender_upper = gender.upper() if gender else None

    results: list[dict[str, Any]] = []
    for v in resp.voices:
        gender_name = tts.SsmlVoiceGender(v.ssml_gender).name
        if gender_upper and gender_name != gender_upper:
            continue
        if name_contains and name_contains.lower() not in v.name.lower():
            continue
        results.append(
            {
                "name": v.name,
                "language_codes": list(v.language_codes),
                "ssml_gender": gender_name,
                "natural_sample_rate_hertz": v.natural_sample_rate_hertz,
            }
        )
    return results


# ── Synthesis ────────────────────────────────────────────────────────────────


def synthesize(
    text: str,
    cfg: TTSConfig,
    output_path: Path | None = None,
) -> Path:
    """Synthesize *text* (plain or SSML) and write the audio file.

    Returns the ``Path`` of the written file.
    """
    if not text.strip():
        raise ValueError("Input text must not be empty.")

    client = _get_client()

    # Auto-detect SSML
    is_ssml = text.strip().startswith("<speak>")
    synth_input = (
        tts.SynthesisInput(ssml=text) if is_ssml else tts.SynthesisInput(text=text)
    )

    voice_params = tts.VoiceSelectionParams(
        language_code=cfg.language_code,
        name=cfg.voice_name or None,
    )

    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding(cfg.encoding_enum),
        speaking_rate=cfg.speaking_rate,
        pitch=cfg.pitch,
        volume_gain_db=cfg.volume_gain_db,
    )

    response = client.synthesize_speech(
        input=synth_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    out = output_path or _default_output_path(text, cfg)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(response.audio_content)
    return out


# ── Helpers ──────────────────────────────────────────────────────────────────

_client_instance: tts.TextToSpeechClient | None = None


def _get_client() -> tts.TextToSpeechClient:
    """Lazy-initialise the TTS client (uses ADC or GOOGLE_APPLICATION_CREDENTIALS)."""
    global _client_instance
    if _client_instance is None:
        try:
            _client_instance = tts.TextToSpeechClient()
        except Exception as exc:
            print(
                "\n✖  Could not authenticate with Google Cloud.\n"
                "   Make sure you have run:\n"
                "     gcloud auth application-default login\n"
                "   or set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON.\n",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
    return _client_instance


def _slugify(text: str, max_words: int = 5, max_len: int = 40) -> str:
    words = re.sub(r"[^\w\s-]", "", text).split()[:max_words]
    slug = "_".join(words).lower()
    return slug[:max_len]


def _default_output_path(text: str, cfg: TTSConfig) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = _slugify(text)
    filename = f"{stamp}_{slug}{cfg.file_extension}"
    return _OUTPUTS_DIR / filename

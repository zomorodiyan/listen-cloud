"""Configuration loader – reads config.yaml and merges CLI overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"

ENCODING_MAP: dict[str, int] = {
    "LINEAR16": 1,
    "MP3": 2,
    "OGG_OPUS": 3,
    "MULAW": 5,
    "ALAW": 6,
}

ENCODING_EXTENSIONS: dict[str, str] = {
    "LINEAR16": ".wav",
    "MP3": ".mp3",
    "OGG_OPUS": ".ogg",
    "MULAW": ".wav",
    "ALAW": ".wav",
}


@dataclass
class TTSConfig:
    """Holds settings for voice synthesis."""

    language_code: str = "en-US"
    voice_name: str = ""
    encoding: str = "MP3"
    speaking_rate: float = 1.0
    pitch: float = 0.0
    volume_gain_db: float = 0.0
    cache_ttl_seconds: int = 86_400

    # ── helpers ──────────────────────────────────────────────────────
    @property
    def encoding_enum(self) -> int:
        """Return the protobuf enum int for the chosen encoding."""
        key = self.encoding.upper()
        if key not in ENCODING_MAP:
            raise ValueError(
                f"Unknown encoding '{self.encoding}'. "
                f"Choose from: {', '.join(ENCODING_MAP)}"
            )
        return ENCODING_MAP[key]

    @property
    def file_extension(self) -> str:
        return ENCODING_EXTENSIONS.get(self.encoding.upper(), ".bin")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def load_config(
    config_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> TTSConfig:
    """Load config.yaml, apply *overrides*, and return a ``TTSConfig``."""
    path = config_path or _DEFAULT_CONFIG_PATH
    raw = _load_yaml(path)

    if overrides:
        for k, v in overrides.items():
            if v is not None:
                raw[k] = v

    known_fields = {f.name for f in TTSConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in raw.items() if k in known_fields}
    return TTSConfig(**filtered)

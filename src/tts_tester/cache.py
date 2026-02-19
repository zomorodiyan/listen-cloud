"""Local file-based cache for the voice list (avoids hitting the API every run)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"
_CACHE_FILE = _CACHE_DIR / "voices.json"


def _read_cache() -> dict[str, Any] | None:
    if not _CACHE_FILE.exists():
        return None
    try:
        with open(_CACHE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def get_cached_voices(ttl_seconds: int = 86_400) -> list[dict[str, Any]] | None:
    """Return the cached voice list if it exists and is fresh, else ``None``."""
    data = _read_cache()
    if data is None:
        return None
    cached_at: float = data.get("cached_at", 0)
    if (time.time() - cached_at) > ttl_seconds:
        return None
    voices: list[dict[str, Any]] = data.get("voices", [])
    return voices


def save_voices(voices: list[dict[str, Any]]) -> None:
    """Persist *voices* to the local cache file."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"cached_at": time.time(), "voices": voices}
    with open(_CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def clear_cache() -> None:
    """Delete the cache file if present."""
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()

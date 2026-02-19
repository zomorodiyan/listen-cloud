"""Cross-platform audio playback helper."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def play(filepath: Path) -> None:
    """Try to play *filepath* using the best available method for the OS.

    Falls back to opening the file with the default handler or printing
    a manual command when no suitable player is found.
    """
    system = platform.system()

    if system == "Darwin":
        _try_run(["afplay", str(filepath)], filepath)
    elif system == "Linux":
        _play_linux(filepath)
    elif system == "Windows":
        _play_windows(filepath)
    else:
        _fallback(filepath)


# ── Platform helpers ─────────────────────────────────────────────────────────


def _play_linux(filepath: Path) -> None:
    ext = filepath.suffix.lower()

    # Prefer aplay for WAV, mpv/ffplay/paplay for others
    if ext == ".wav" and shutil.which("aplay"):
        _try_run(["aplay", str(filepath)], filepath)
        return

    for player in ("mpv", "ffplay", "paplay", "xdg-open"):
        if shutil.which(player):
            args = [player]
            if player == "ffplay":
                args += ["-nodisp", "-autoexit"]
            args.append(str(filepath))
            _try_run(args, filepath)
            return

    _fallback(filepath)


def _play_windows(filepath: Path) -> None:
    ext = filepath.suffix.lower()
    if ext == ".wav":
        # PowerShell SoundPlayer works for WAV without extra deps
        ps_cmd = (
            f'(New-Object Media.SoundPlayer "{filepath}").PlaySync()'
        )
        _try_run(["powershell", "-Command", ps_cmd], filepath)
    else:
        # 'start' opens with the default handler
        _try_run(["cmd", "/c", "start", "", str(filepath)], filepath)


# ── Internals ────────────────────────────────────────────────────────────────


def _try_run(cmd: list[str], filepath: Path) -> None:
    exe = cmd[0]
    if not shutil.which(exe) and exe not in ("cmd", "powershell"):
        _fallback(filepath)
        return
    try:
        print(f"▶  Playing with {exe} …")
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        _fallback(filepath)
    except subprocess.CalledProcessError as exc:
        print(f"⚠  Playback exited with code {exc.returncode}.", file=sys.stderr)


def _fallback(filepath: Path) -> None:
    print(
        f"ℹ  Could not find an audio player.\n"
        f"   Open the file manually:\n"
        f"     {filepath.resolve()}"
    )

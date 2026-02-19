"""Cross-platform audio playback helper (includes WSL support)."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _is_wsl() -> bool:
    """Detect if we're running inside Windows Subsystem for Linux."""
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _wsl_to_windows_path(filepath: Path) -> str:
    """Convert a Linux path to a Windows path using wslpath."""
    try:
        result = subprocess.run(
            ["wslpath", "-w", str(filepath.resolve())],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback: manual conversion for /home → \\wsl$\ paths
        return str(filepath.resolve())


def play(filepath: Path) -> None:
    """Try to play *filepath* using the best available method for the OS.

    Falls back to opening the file with the default handler or printing
    a manual command when no suitable player is found.
    """
    if _is_wsl():
        _play_wsl(filepath)
        return

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


def _play_wsl(filepath: Path) -> None:
    """Play audio from WSL by invoking Windows-side tools."""
    win_path = _wsl_to_windows_path(filepath)

    # Try powershell.exe (available in WSL by default)
    if shutil.which("powershell.exe"):
        ext = filepath.suffix.lower()
        if ext == ".wav":
            ps_cmd = f'(New-Object Media.SoundPlayer "{win_path}").PlaySync()'
            _try_run(["powershell.exe", "-Command", ps_cmd], filepath)
        else:
            # Start with default Windows handler (non-blocking but works)
            _try_run(
                ["powershell.exe", "-Command", f'Start-Process "{win_path}"'],
                filepath,
            )
        return

    # Fallback: cmd.exe
    if shutil.which("cmd.exe"):
        _try_run(["cmd.exe", "/c", "start", "", win_path], filepath)
        return

    _fallback(filepath)


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
        ps_cmd = (
            f'(New-Object Media.SoundPlayer "{filepath}").PlaySync()'
        )
        _try_run(["powershell", "-Command", ps_cmd], filepath)
    else:
        _try_run(["cmd", "/c", "start", "", str(filepath)], filepath)


# ── Internals ────────────────────────────────────────────────────────────────


def _try_run(cmd: list[str], filepath: Path) -> None:
    exe = cmd[0]
    if not shutil.which(exe) and exe not in ("cmd", "cmd.exe", "powershell", "powershell.exe"):
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

"""CLI entry-point for tts-tester (argparse-based)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from tts_tester import __version__
from tts_tester.cache import clear_cache, get_cached_voices, save_voices
from tts_tester.config import TTSConfig, load_config
from tts_tester.player import play
from tts_tester.tts import list_voices, synthesize


# ═══════════════════════════════════════════════════════════════════════════
#  Argument parser
# ═══════════════════════════════════════════════════════════════════════════


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tts-tester",
        description="Google Cloud Text-to-Speech tester – synthesize & play audio.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config YAML file (default: config.yaml in project root).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── voices ───────────────────────────────────────────────────────
    vp = sub.add_parser("voices", help="List available voices.")
    vp.add_argument("-l", "--lang", default=None, help="Filter by language_code (e.g. en-US).")
    vp.add_argument("-n", "--name", default=None, help="Filter by voice name substring.")
    vp.add_argument("-g", "--gender", default=None, help="Filter by gender (MALE, FEMALE, NEUTRAL).")
    vp.add_argument("--refresh", action="store_true", help="Ignore local cache and fetch from API.")

    # ── synth ────────────────────────────────────────────────────────
    sp = sub.add_parser("synth", help="Synthesize text to audio.")
    sp.add_argument("text", nargs="?", default=None, help="Text (or SSML) to synthesize.")
    sp.add_argument("-f", "--file", type=Path, default=None, help="Read input from a text file instead.")
    sp.add_argument("-l", "--lang", default=None, dest="language_code", help="Language code (e.g. en-US).")
    sp.add_argument("-v", "--voice", default=None, dest="voice_name", help="Exact voice name.")
    sp.add_argument("-e", "--encoding", default=None, help="Audio encoding (MP3, LINEAR16, OGG_OPUS, …).")
    sp.add_argument("-r", "--rate", type=float, default=None, dest="speaking_rate", help="Speaking rate (0.25–4.0).")
    sp.add_argument("-p", "--pitch", type=float, default=None, help="Pitch in semitones (-20 to 20).")
    sp.add_argument("--volume", type=float, default=None, dest="volume_gain_db", help="Volume gain dB (-96 to 16).")
    sp.add_argument("-o", "--output", type=Path, default=None, help="Output file path.")
    sp.add_argument("--no-play", action="store_true", help="Skip automatic playback.")

    # ── interactive ──────────────────────────────────────────────────
    sub.add_parser("interactive", help="Launch interactive prompt mode.")

    return parser


# ═══════════════════════════════════════════════════════════════════════════
#  Command handlers
# ═══════════════════════════════════════════════════════════════════════════


def _cmd_voices(args: argparse.Namespace, cfg: TTSConfig) -> None:
    """Handle the ``voices`` subcommand."""
    if not args.refresh:
        cached = get_cached_voices(ttl_seconds=cfg.cache_ttl_seconds)
        if cached is not None:
            voices = cached
            # Apply client-side filters on cached data
            if args.lang:
                voices = [v for v in voices if any(args.lang.lower() in lc.lower() for lc in v["language_codes"])]
            if args.name:
                voices = [v for v in voices if args.name.lower() in v["name"].lower()]
            if args.gender:
                voices = [v for v in voices if v["ssml_gender"].upper() == args.gender.upper()]
            _print_voices(voices)
            return
    else:
        clear_cache()

    print("Fetching voices from Google Cloud …")
    try:
        voices = list_voices(
            language_code=args.lang,
            name_contains=args.name,
            gender=args.gender,
        )
    except Exception as exc:
        print(f"✖  Failed to list voices: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    # Cache the *unfiltered* set so later runs benefit
    all_voices = list_voices() if (args.lang or args.name or args.gender) else voices
    save_voices(all_voices)

    _print_voices(voices)


def _print_voices(voices: list[dict]) -> None:
    if not voices:
        print("No voices matched your filters.")
        return
    print(f"\n{'Voice Name':<40} {'Lang':<10} {'Gender':<10} {'Hz':>6}")
    print("─" * 70)
    for v in voices:
        langs = ", ".join(v["language_codes"])
        print(f"{v['name']:<40} {langs:<10} {v['ssml_gender']:<10} {v['natural_sample_rate_hertz']:>6}")
    print(f"\nTotal: {len(voices)} voice(s)\n")


def _cmd_synth(args: argparse.Namespace, cfg: TTSConfig) -> None:
    """Handle the ``synth`` subcommand."""
    text = _resolve_text(args)

    # Apply CLI overrides onto config
    overrides = {
        k: getattr(args, k)
        for k in ("language_code", "voice_name", "encoding", "speaking_rate", "pitch", "volume_gain_db")
        if getattr(args, k, None) is not None
    }
    for k, v in overrides.items():
        setattr(cfg, k, v)

    print(f"Synthesizing ({cfg.encoding}, rate={cfg.speaking_rate}, pitch={cfg.pitch}) …")
    try:
        out = synthesize(text, cfg, output_path=args.output)
    except ValueError as exc:
        print(f"✖  {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"✖  Synthesis failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    size_kb = out.stat().st_size / 1024
    print(f"✔  Saved to {out}  ({size_kb:.1f} KB)")

    if not args.no_play:
        play(out)


def _resolve_text(args: argparse.Namespace) -> str:
    """Return the text to synthesize from positional arg or --file."""
    if args.file:
        p: Path = args.file
        if not p.exists():
            print(f"✖  File not found: {p}", file=sys.stderr)
            raise SystemExit(1)
        return p.read_text(encoding="utf-8")
    if args.text:
        return args.text
    # Fall back to stdin if piped
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("✖  No text provided. Pass text as an argument, use --file, or pipe via stdin.", file=sys.stderr)
    raise SystemExit(1)


def _cmd_interactive(cfg: TTSConfig) -> None:
    """Run a simple interactive REPL."""
    print("┌──────────────────────────────────────────────┐")
    print("│  TTS Tester – Interactive Mode               │")
    print("│  Type text and press Enter to synthesize.    │")
    print("│  Commands: /voices  /config  /quit           │")
    print("└──────────────────────────────────────────────┘")

    while True:
        try:
            text = input("\n🎤  ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not text:
            continue
        if text.lower() in ("/quit", "/exit", "/q"):
            print("Bye!")
            break
        if text.lower() == "/voices":
            try:
                voices = list_voices(language_code=cfg.language_code)
                _print_voices(voices)
            except Exception as exc:
                print(f"✖  {exc}", file=sys.stderr)
            continue
        if text.lower() == "/config":
            for field_name in TTSConfig.__dataclass_fields__:
                print(f"  {field_name}: {getattr(cfg, field_name)}")
            continue

        try:
            out = synthesize(text, cfg)
            size_kb = out.stat().st_size / 1024
            print(f"✔  {out}  ({size_kb:.1f} KB)")
            play(out)
        except Exception as exc:
            print(f"✖  {exc}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    cfg = load_config(config_path=args.config)

    match args.command:
        case "voices":
            _cmd_voices(args, cfg)
        case "synth":
            _cmd_synth(args, cfg)
        case "interactive":
            _cmd_interactive(cfg)
        case _:
            parser.print_help()

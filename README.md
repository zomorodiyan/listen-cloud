# 🔊 Google Cloud Text-to-Speech Tester

A lightweight local tool for quickly synthesizing speech with Google Cloud TTS, listening to it, and iterating on voice/speed/pitch settings — right from VS Code.

**Two interfaces:**

| Interface | When to use |
|-----------|-------------|
| **CLI** (`python -m tts_tester`) | Fast one-liners and scripting |
| **Streamlit UI** (`streamlit run app.py`) | Visual exploration of voices & settings |

---

## Prerequisites

- Python 3.10+
- A GCP project with the **Cloud Text-to-Speech API** enabled
- `gcloud` CLI installed (for ADC login) **or** a service-account JSON key

---

## 1 · Setup in VS Code

```bash
# Clone / open this folder in VS Code, then open a terminal (Ctrl+`)

# Create & activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows PowerShell

# Install the package (editable) with all dependencies
pip install -e ".[ui]"         # includes Streamlit
# pip install -e .             # without Streamlit
```

Or simply:

```bash
make install          # creates .venv, installs everything
source .venv/bin/activate
```

---

## 2 · Authentication

You need **one** of the two options below.

### Option A – Application Default Credentials (recommended for dev)

```bash
gcloud auth application-default login
```

This opens a browser, you log in, and a local credential file is saved.  
The TTS client picks it up automatically.

### Option B – Service-account JSON

1. In the GCP Console → IAM → Service Accounts, create a key (JSON).
2. Download the file (e.g. `my-sa-key.json`). **Do not commit it.**
3. Set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/my-sa-key.json"
```

> **Tip:** add the export to your `.env` file and use the VS Code *Python: Env File* setting, or add it to `.venv/bin/activate`.

---

## 3 · Configuration

Edit **`config.yaml`** in the project root to change defaults:

```yaml
language_code: "en-US"
voice_name: ""          # leave empty for API default
encoding: "MP3"         # MP3 | LINEAR16 | OGG_OPUS | MULAW | ALAW
speaking_rate: 1.0      # 0.25 – 4.0
pitch: 0.0              # -20.0 – 20.0
volume_gain_db: 0.0     # -96.0 – 16.0
cache_ttl_seconds: 86400
```

All values can be overridden per-call via CLI flags (see below).

---

## 4 · CLI Usage

### List voices

```bash
python -m tts_tester voices                       # all voices (cached)
python -m tts_tester voices --lang en-US           # English (US) only
python -m tts_tester voices --gender FEMALE         # female voices
python -m tts_tester voices --name Wavenet          # names containing "Wavenet"
python -m tts_tester voices --refresh               # force refresh from API
```

### Synthesize speech

```bash
python -m tts_tester synth "Hello, world!"
python -m tts_tester synth "Hola mundo" --lang es-ES
python -m tts_tester synth "Fast!" --rate 1.5 --pitch 2
python -m tts_tester synth "<speak>Hello <break time='500ms'/> world</speak>"
python -m tts_tester synth --file input.txt --encoding OGG_OPUS
python -m tts_tester synth "No play" --no-play
echo "piped text" | python -m tts_tester synth
```

The audio file is saved to `outputs/` with a timestamped name and played automatically.

### Interactive mode

```bash
python -m tts_tester interactive
```

Type text and press Enter to hear it immediately. Commands inside the REPL:

| Command | Action |
|---------|--------|
| `/voices` | List voices for current language |
| `/config` | Show active settings |
| `/quit` | Exit |

### Makefile shortcuts

```bash
make voices                      # list voices
make synth                       # synthesize "Hello world"
make synth TEXT="Custom text"    # synthesize custom text
make run                         # interactive mode
make ui                          # launch Streamlit
make clean                       # delete outputs & cache
```

---

## 5 · Streamlit Web UI (optional)

```bash
pip install -e ".[ui]"    # if not already installed
streamlit run app.py
```

Features:
- Text box for plain text or SSML
- Voice dropdown (auto-populated from API, cached)
- Sliders for speed, pitch, volume
- In-browser audio playback + download button

---

## 6 · Project Structure

```
listen-cloud/
├── pyproject.toml          # Package metadata & dependencies
├── config.yaml             # Default TTS settings
├── Makefile                # Convenience targets
├── app.py                  # Streamlit web UI (optional)
├── README.md
├── outputs/                # Generated audio files (auto-created)
│   └── .gitkeep
└── src/
    └── tts_tester/
        ├── __init__.py     # Package version
        ├── __main__.py     # python -m entry-point
        ├── cli.py          # Argparse CLI (voices / synth / interactive)
        ├── tts.py          # Google Cloud TTS API wrapper
        ├── player.py       # Cross-platform audio playback
        ├── config.py       # YAML config loader
        └── cache.py        # Voice-list cache with TTL
```

---

## 7 · Windows Notes

If you're on Windows and don't have `make`:

```powershell
# Create venv
python -m venv .venv
.venv\Scripts\activate

# Install
pip install -e ".[ui]"

# Run commands directly
python -m tts_tester voices
python -m tts_tester synth "Hello world"
python -m tts_tester interactive
streamlit run app.py
```

WAV files play via PowerShell's `SoundPlayer`; MP3/OGG files open with the default media player.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Could not authenticate with Google Cloud` | Run `gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS` |
| `Permission denied` on the TTS API | Ensure the API is enabled in your GCP project and the account has the `roles/cloudtexttospeech.user` role |
| `No voices matched your filters` | Try broader filters or `--refresh` to update the cache |
| Audio doesn't play automatically | Install `mpv` or `ffplay`, or open the file path printed in the output |

"""Streamlit web UI for Google Cloud Text-to-Speech Tester.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src/ package is importable when running via `streamlit run app.py`
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

from tts_tester.cache import get_cached_voices, save_voices
from tts_tester.config import ENCODING_MAP, load_config
from tts_tester.tts import list_voices, synthesize

st.set_page_config(page_title="TTS Tester", page_icon="🔊", layout="centered")
st.title("🔊 Google Cloud TTS Tester")

cfg = load_config()

# ── Sidebar: voice browser ──────────────────────────────────────────────────

with st.sidebar:
    st.header("Voice browser")
    refresh = st.button("🔄 Refresh voice list")

    voices = None
    if not refresh:
        voices = get_cached_voices(ttl_seconds=cfg.cache_ttl_seconds)

    if voices is None:
        with st.spinner("Fetching voices …"):
            try:
                voices = list_voices()
                save_voices(voices)
            except Exception as exc:
                st.error(f"Failed to fetch voices: {exc}")
                voices = []

    # Language filter
    all_langs = sorted({lc for v in voices for lc in v["language_codes"]})
    lang_filter = st.selectbox("Language", ["(all)"] + all_langs, index=0)

    filtered = voices
    if lang_filter != "(all)":
        filtered = [v for v in filtered if lang_filter in v["language_codes"]]

    voice_names = [v["name"] for v in filtered]
    st.caption(f"{len(voice_names)} voice(s)")

# ── Main area ────────────────────────────────────────────────────────────────

text = st.text_area("Text or SSML to synthesize", height=150, placeholder="Hello, world!")

col1, col2 = st.columns(2)
with col1:
    language_code = st.text_input("Language code", value=cfg.language_code)
    encoding = st.selectbox("Encoding", list(ENCODING_MAP.keys()), index=list(ENCODING_MAP.keys()).index(cfg.encoding))
with col2:
    voice_name = st.selectbox("Voice", ["(default)"] + voice_names)
    if voice_name == "(default)":
        voice_name = ""

col3, col4, col5 = st.columns(3)
with col3:
    speaking_rate = st.slider("Speed", 0.25, 4.0, cfg.speaking_rate, step=0.05)
with col4:
    pitch = st.slider("Pitch", -20.0, 20.0, cfg.pitch, step=0.5)
with col5:
    volume_gain_db = st.slider("Volume dB", -10.0, 10.0, cfg.volume_gain_db, step=0.5)

if st.button("🎧 Generate", type="primary"):
    if not text.strip():
        st.warning("Please enter some text.")
    else:
        scfg = load_config(
            overrides={
                "language_code": language_code,
                "voice_name": voice_name,
                "encoding": encoding,
                "speaking_rate": speaking_rate,
                "pitch": pitch,
                "volume_gain_db": volume_gain_db,
            }
        )
        with st.spinner("Synthesizing …"):
            try:
                out = synthesize(text, scfg)
            except Exception as exc:
                st.error(f"Synthesis failed: {exc}")
                st.stop()

        st.success(f"Saved to `{out.name}` ({out.stat().st_size / 1024:.1f} KB)")

        mime = {
            "MP3": "audio/mpeg",
            "OGG_OPUS": "audio/ogg",
            "LINEAR16": "audio/wav",
            "MULAW": "audio/wav",
            "ALAW": "audio/wav",
        }.get(encoding, "audio/mpeg")

        st.audio(out.read_bytes(), format=mime)
        st.download_button("⬇ Download", data=out.read_bytes(), file_name=out.name, mime=mime)

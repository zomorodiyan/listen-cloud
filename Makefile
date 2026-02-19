.PHONY: install run voices synth interactive ui clean help

PYTHON ?= python3

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:         ## Create venv and install dependencies
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[ui]"
	@echo "\n✔  Installed. Activate with:  source .venv/bin/activate"

run:             ## Alias for interactive mode
	$(PYTHON) -m tts_tester interactive

voices:          ## List available voices
	$(PYTHON) -m tts_tester voices

synth:           ## Synthesize "Hello world" (override TEXT= to change)
	$(PYTHON) -m tts_tester synth "$(or $(TEXT),Hello world)"

interactive:     ## Launch interactive REPL
	$(PYTHON) -m tts_tester interactive

ui:              ## Launch Streamlit web UI
	streamlit run app.py

clean:           ## Remove outputs and cache
	rm -rf outputs/*.mp3 outputs/*.wav outputs/*.ogg .cache/
	@echo "✔  Cleaned outputs and cache."

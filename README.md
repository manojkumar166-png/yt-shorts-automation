# Low-RAM Free Automated YouTube Generator

Optimized for computers with low RAM. This version **completely eliminates Ollama and heavy local LLMs**, running entirely on lightweight scripts and free cloud endpoints (Edge-TTS) with minimal resource usage.

## Features
- **No Ollama / No Local LLM Required:** Runs instantly without eating up your RAM.
- **Voiceover:** Microsoft Edge TTS (`edge-tts` — 100% free, zero installation overhead).
- **Video Assembly:** Lightweight MoviePy rendering optimized with `ultrafast` presets.

## Quickstart

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Generator:**
   ```bash
   python main.py
   ```

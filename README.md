# YouTube Shorts Automation

A GitHub Actions pipeline that selects a script, creates narration, generates four AI background visuals, and renders a vertical 1080×1920 MP4.

## Pipeline

1. **Queue** — `main.py` selects the next unused entry from `script_bank.json` and records progress in `state.json`.
2. **Narration** — `audio.py` uses Edge-TTS, with gTTS as a fallback.
3. **AI visuals** — `fetch_background.py` calls `asset_fetcher.py`. Anonymous OVHcloud SDXL is tried first without credentials. If it is unavailable or fails, anonymous AI Horde is used automatically.
4. **Render** — `CreateVideo.py` assembles the vertical video, motion, narration, and subtitles.
5. **Artifact** — GitHub Actions uploads generated MP4 files as a workflow artifact.

Wikipedia and Pixabay image fetching have been removed. The only non-AI fallback is a simple gradient so the render can continue if both AI providers are unavailable.

## Image generation providers

### 1. OVHcloud SDXL (anonymous, no API key)

The project uses OVHcloud's public Stable Diffusion XL endpoint:

`https://stable-diffusion-xl.endpoints.kepler.ai.cloud.ovh.net/api/text2image`

The request does not include an API key, access token, account secret, or authorization header. The client spaces requests 31 seconds apart to respect the public endpoint's two-requests-per-minute limit. Public service availability and rate limits may change.

### 2. AI Horde (anonymous fallback)

No registration, account, or user-supplied API key is required. The integration uses AI Horde's public anonymous identity (`0000000000`). Anonymous requests have the lowest queue priority, so generation can be slow or unavailable when volunteer workers are busy. The code waits up to 15 minutes per image before falling back.

AI Horde is community-powered. Prompts and generated images are processed by volunteer workers; do not send private or sensitive material.

### Fallback order

1. Anonymous OVHcloud SDXL.
2. Anonymous AI Horde, with no user-supplied key.
3. Gradient background only if both image generators fail.

The pipeline generates images only for the video currently being rendered; it does not pre-generate visuals for a batch of unused scripts. The providers generate images at their supported dimensions, which the renderer crops/resizes to the 9:16 canvas. Prompts keep the main subject near the center.

**Cost note:** These anonymous endpoints do not require user API keys. Availability, queueing, usage limits, and provider policies are controlled by the respective services and may change.

## Run on GitHub Actions

1. Open the **Actions** tab.
2. Select **daily-shorts**.
3. Click **Run workflow**.
4. Download the generated MP4 files from the workflow run's **Artifacts** section.

The workflow also runs on its configured daily schedule.

## Script format

Add entries to `script_bank.json`:

```json
[
  {
    "topic": "the deep ocean",
    "hook": "We know more about the surface of Mars than our own oceans.",
    "facts": [
      "The ocean is still largely unexplored.",
      "The Mariana Trench is the deepest known part of the ocean.",
      "Some deep-sea animals produce their own light."
    ],
    "image_queries": [
      "deep ocean",
      "underwater",
      "bioluminescent jellyfish",
      "ocean trench"
    ]
  }
]
```

Use four short visual subjects for `image_queries`. They are expanded into cinematic image-generation prompts.

## Main files

| File | Responsibility |
| --- | --- |
| `main.py` | Script queue, retries, and orchestration |
| `audio.py` | Text-to-speech |
| `fetch_background.py` | Visual stage entry point |
| `asset_fetcher.py` | Image cache, provider order, and fallback |
| `ovhcloud_image.py` | Anonymous OVHcloud SDXL API client |
| `ai_horde_image.py` | Anonymous AI Horde API client |
| `CreateVideo.py` | Vertical video rendering |
| `.github/workflows/generate.yml` | Scheduled and manual GitHub Actions workflow |

## Local run

Install Python dependencies and system packages (FFmpeg and ImageMagick), then run:

```bash
pip install -r requirements.txt
python main.py
```

Both image providers work without user API keys or environment variables. Generated MP4 files are written to `output/`.

# YouTube Shorts Automation

A GitHub Actions pipeline that selects a script, creates narration, generates four AI background visuals, and renders a vertical 1080×1920 MP4.

## Pipeline

1. **Queue** — `main.py` selects the next unused entry from `script_bank.json` and records progress in `state.json`.
2. **Narration** — `audio.py` uses Edge-TTS, with gTTS as a fallback.
3. **AI visuals** — `fetch_background.py` calls `asset_fetcher.py`. OVHcloud SDXL is tried first when its access token is configured. If it is not configured or fails, anonymous AI Horde is used automatically without an account or API key.
4. **Render** — `CreateVideo.py` assembles the vertical video, motion, narration, and subtitles.
5. **Artifact** — GitHub Actions uploads generated MP4 files as a workflow artifact.

Wikipedia and Pixabay image fetching have been removed. The only non-AI fallback is a simple gradient so the render can continue if both AI providers are unavailable.

## Image generation providers

### 1. OVHcloud SDXL (preferred, optional)

The project retains the OVHcloud AI Endpoints integration with the Stable Diffusion XL model.

1. Create an OVHcloud Public Cloud project and configure a payment method.
2. Open **AI & Machine Learning → AI Endpoints**, create an API access key, and review current model pricing and account conditions.
3. In this GitHub repository, open **Settings → Secrets and variables → Actions**.
4. Add a repository secret named `OVH_AI_ENDPOINTS_ACCESS_TOKEN` and paste the OVHcloud access token as its value.

When this secret is present, OVHcloud is attempted first for each image.

### 2. AI Horde (automatic anonymous fallback)

No registration, account, or API key is required. The integration uses AI Horde's public anonymous identity (`0000000000`). Anonymous requests have the lowest queue priority, so generation can be slow or unavailable when volunteer workers are busy. The code waits up to 15 minutes per image before falling back.

AI Horde is community-powered and free to use anonymously, subject to service availability and request limits. Prompts and generated images are processed by volunteer workers; do not send private or sensitive material.

### Fallback order

1. OVHcloud SDXL, if configured.
2. Anonymous AI Horde, with no user-supplied key.
3. Gradient background only if both image generators fail.

The pipeline generates images only for the video currently being rendered; it does not pre-generate visuals for a batch of unused scripts. The providers currently generate 512×768 (AI Horde) or 1024×1024 (OVHcloud) images, which the renderer crops/resizes to the 9:16 canvas. Prompts keep the main subject near the center.

**Cost note:** AI Horde anonymous use does not require a paid account, but it has the lowest queue priority. OVHcloud may incur charges; review its current pricing and quotas before adding the secret.

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
| `ovhcloud_image.py` | OVHcloud SDXL API client |
| `ai_horde_image.py` | Anonymous AI Horde API client |
| `CreateVideo.py` | Vertical video rendering |
| `.github/workflows/generate.yml` | Scheduled and manual GitHub Actions workflow |

## Local run

Install Python dependencies and system packages (FFmpeg and ImageMagick), set the optional OVHcloud token if desired, then run:

```bash
pip install -r requirements.txt
python main.py
```

AI Horde works without environment variables or API keys. Generated MP4 files are written to `output/`.

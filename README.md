# YouTube Shorts Automation

A GitHub Actions pipeline that selects a script, creates narration, gathers or generates four background visuals, and renders a vertical 1080×1920 MP4.

## Pipeline

1. **Queue** — `main.py` selects the next unused entry from `script_bank.json` and records progress in `state.json`.
2. **Narration** — `audio.py` uses Edge-TTS, with gTTS as a fallback.
3. **Visuals** — `fetch_background.py` calls `asset_fetcher.py`. When configured, OVHcloud SDXL generates visuals for the active video. If OVHcloud is not configured or fails, the fetcher falls back to Wikipedia, Pixabay (when configured), and finally a gradient.
4. **Render** — `CreateVideo.py` assembles the vertical video, motion, music/narration track, and word-timed subtitles.
5. **Artifact** — GitHub Actions uploads generated MP4 files as a short-lived workflow artifact.

## OVHcloud image generation (optional)

The project uses OVHcloud AI Endpoints with the Stable Diffusion XL model. The integration is optional: without a token, the existing stock-image fallback chain continues to work.

1. Create an OVHcloud Public Cloud project and configure a payment method.
2. Open **AI & Machine Learning → AI Endpoints**, create an API access key, and check the current model catalogue and pricing/conditions.
3. In this GitHub repository, open **Settings → Secrets and variables → Actions**.
4. Add a repository secret named:

   `OVH_AI_ENDPOINTS_ACCESS_TOKEN`

   Paste the OVHcloud AI Endpoints access key as its value.

5. Run **Actions → daily-shorts → Run workflow**.

OVHcloud AI image generation is only used when generating the selected video. The 14-script stock-image prefetch deliberately does **not** call OVHcloud, to avoid generating (and potentially paying for) images for videos that are not being rendered.

The current OVHcloud SDXL endpoint returns 1024×1024 images. The video renderer crops/resizes them to fill the 9:16 canvas, so keep the main subject near the center in prompts.

**Cost note:** Do not assume the service is permanently free. OVHcloud's access-key setup currently requires a Public Cloud project with a payment method. Review the model catalogue, pricing, quotas, and account terms before enabling it. If the secret is absent, the pipeline uses the non-AI image providers.

## Existing stock-image setup

Add a repository secret named `PIXABAY_API_KEY` if you want Pixabay as an additional fallback. Wikipedia media search is attempted without a key. The pipeline can still render a gradient background if all image sources fail.

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

Use four short visual subjects for `image_queries`. OVHcloud turns each subject into an image prompt; the stock providers use it as a search phrase.

## Main files

| File | Responsibility |
| --- | --- |
| `main.py` | Script queue, retries, and orchestration |
| `audio.py` | Text-to-speech |
| `fetch_background.py` | Visual stage entry point |
| `asset_fetcher.py` | Cache, OVHcloud/stock provider fallback, and image validation |
| `ovhcloud_image.py` | OVHcloud SDXL API client |
| `prefetch.py` | Stock-only prefetch for upcoming scripts |
| `CreateVideo.py` | Vertical video rendering |
| `.github/workflows/generate.yml` | Scheduled and manual GitHub Actions workflow |

## Local run

Install Python dependencies and system packages (FFmpeg and ImageMagick), set any provider keys in your environment, then run:

```bash
pip install -r requirements.txt
python main.py
```

Generated MP4 files are written to `output/`.

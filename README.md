# YouTube Shorts Automation

A GitHub Actions pipeline that selects unused scripts, creates narration, generates four AI background visuals, and renders vertical 1080×1920 MP4s.

## Pipeline

1. **Script queue** — `main.py` selects the next unused entry from `script_bank.json`.
2. **Fresh scripts** — when the bank has no unused scripts, `generate_scripts.py` asks Gemini (with Google Search grounding enabled) to research and create a new batch.
3. **One-time use** — successful topics are permanently recorded in `state.json`. A topic is never selected again. A script that fails three times is retired rather than recycled.
4. **Narration** — `audio.py` uses Edge-TTS, with gTTS as a fallback.
5. **AI visuals** — anonymous OVHcloud SDXL is tried first; anonymous AI Horde is the fallback; a gradient is used only if both fail.
6. **Render and artifact** — the pipeline renders the video and uploads MP4 files as GitHub Actions artifacts.

## Gemini setup (required for new scripts)

1. Create a Gemini API key in Google AI Studio.
2. Open this repository's **Settings → Secrets and variables → Actions → New repository secret**.
3. Add the secret named `GEMINI_API_KEY`.
4. Optionally add a repository variable `GEMINI_MODEL`; default is `gemini-2.5-flash`.

Gemini is called only when there are no unused scripts left in `script_bank.json`. It generates a batch of 10 at a time. Generated scripts are committed back to the repository along with usage state, so future runs continue from the saved queue rather than generating the same batch again.

## Image generation providers

### 1. OVHcloud SDXL (anonymous, no API key)

Uses the public Stable Diffusion XL endpoint without an authorization header. Requests are spaced 31 seconds apart to respect the endpoint's stated two-requests-per-minute limit. Availability and public rate limits may change.

### 2. AI Horde (anonymous fallback)

Uses AI Horde's public anonymous identity; no user-supplied API key is needed. Anonymous requests have the lowest queue priority and can be slow. The client waits up to 15 minutes per image.

### Fallback order

1. Anonymous OVHcloud SDXL.
2. Anonymous AI Horde.
3. Gradient background if both generators fail.

Do not send private or sensitive prompts to public image-generation services.

## Scheduling

The workflow creates up to 5 videos per scheduled run (configurable with `VIDEOS_PER_DAY`). Manual runs also create up to 5. Change the workflow environment value if you want a different quota.

## Script quality and retention safeguards

- Gemini drafts three hook alternatives and selects its strongest; the selected hook is used for narration.
- Scripts build a curiosity gap, escalate across three factual beats, and deliver a payoff in the final beat.
- Gemini is instructed to research with Google Search grounding and attach 3–6 source URLs plus an explicit `uncertain_claims` list.
- URLs are checked for HTTPS structure, not independently audited. Review the linked sources and any uncertain claims before publishing; source links alone do not guarantee factual accuracy.
- Each script is categorized. The queue avoids categories used in the previous two videos when another category is available.
- A deterministic quality gate scores hook length, fact concision, image-prompt distinctness, source count and uncertainty flags. Scripts below 70/100 are rejected; set `MIN_SCRIPT_QUALITY_SCORE` to change the threshold.

## Improvements included

- Three hook alternatives with Gemini selecting the strongest; curiosity-gap and payoff structure.
- Exactly three concise narration facts and four visual prompts per script.
- Gemini JSON/schema validation, research source URLs, uncertainty flags, category diversity and quality scoring.
- Batch generation (10 scripts) to reduce repeated API calls.
- Permanent consumed-topic history; no automatic queue reset.
- Failed topics are retired after three attempts to prevent endless repeats.
- Atomic writes for the script bank and state file.
- If `state.json` is corrupt, the run stops instead of erasing history and accidentally repeating content.

## Main files

| File | Responsibility |
| --- | --- |
| `main.py` | Script queue, one-time use, orchestration |
| `generate_scripts.py` | Gemini script generation and validation |
| `script_bank.json` | Pending and generated scripts |
| `state.json` | Permanent used-topic and failure history |
| `audio.py` | Text-to-speech |
| `asset_fetcher.py` | Image cache and provider fallback |
| `ovhcloud_image.py` | Anonymous OVHcloud SDXL client |
| `ai_horde_image.py` | Anonymous AI Horde client |
| `.github/workflows/generate.yml` | Scheduled/manual workflow |

## Run locally

Set `GEMINI_API_KEY` in your environment, install requirements and system packages (FFmpeg and ImageMagick), then run:

```bash
pip install -r requirements.txt
python main.py
```

# YouTube Shorts Automation

A GitHub Actions pipeline that selects unused scripts, creates approximately one minute of narration, generates six AI background visuals, and renders vertical 1080×1920 MP4s.

## Pipeline

1. **Script queue** — `main.py` selects the next unused entry from `script_bank.json`.
2. **Daily fresh scripts** — on every scheduled or manual run, `main.py` asks Gemini (with Google Search grounding enabled) to generate a brand-new script for each video planned in that run. It never fills the day's quota from older queued scripts.
3. **One-time use** — successful topics are permanently recorded in `state.json`. A topic is never selected again. A script that fails three times is retired rather than recycled.
4. **Narration** — `audio.py` uses Edge-TTS, with gTTS as a fallback.
5. **AI visuals** — six 9:16 portrait images are generated per video. Anonymous OVHcloud SDXL is tried first; anonymous AI Horde is the fallback; a gradient is used only if both fail.
6. **Render and delivery** — the pipeline renders each video, sends it to the configured Telegram chat, and uploads MP4 files as GitHub Actions artifacts.

## Gemini setup (required for new scripts)

1. Create a Gemini API key in Google AI Studio.
2. Open this repository's **Settings → Secrets and variables → Actions → New repository secret**.
3. Add the secret named `GEMINI_API_KEY`.
4. Optionally add a repository variable `GEMINI_MODEL`; default is `gemini-2.5-flash`.

Gemini is called on every scheduled or manual run and generates exactly the number of fresh scripts needed for that run (five by default). Existing unused entries are not recycled to fill a day's quota. New scripts and usage history are committed back to the repository. If Gemini generation fails, the workflow stops rather than silently reusing older scripts.

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
- Approximately one-minute narration at a natural TTS pace, with actual speech and rendered durations printed in the Actions log.
- Six 9:16 portrait scenes per video, rendered at 1080×1920.
- Exactly five narration facts and six distinct visual prompts per script, aiming for approximately 60 seconds of narration.
- Gemini JSON/schema validation, research source URLs, uncertainty flags, category diversity and quality scoring.
- Daily generation: Gemini creates a new script for every planned video on each run.
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


## Telegram delivery

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Start a chat with the bot (send `/start`), or add it to the target group/channel. For a channel, make the bot an administrator with permission to post.
3. Find the destination chat ID. Channel IDs commonly begin with `-100`.
4. In GitHub, open **Settings → Secrets and variables → Actions** and add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
5. Run the workflow manually once to test delivery. Each successfully rendered video is sent to Telegram; if Telegram is not configured, videos remain available as Actions artifacts.

Keep the bot token private. Do not paste it into source files or commit it.

# Canva Series — separate 30-second tutorial pipeline

This directory is independent of the existing ~70-second Shorts generator. It reads user-provided screenshots committed to GitHub, builds a 9:16 MP4, and does not edit or replace the original generator.

## Day 1 inputs

Add six screenshots (PNG/JPG/JPEG/WEBP) to `canva-series/assets/day01/` with these exact names:

- `screen-01.png` — open Canva / start a project
- `screen-02.png` — import your screenshots or clips
- `screen-03.png` — arrange the timeline
- `screen-04.png` — add titles or captions
- `screen-05.png` — add voiceover / sound
- `screen-06.png` — export settings

You can use JPG/JPEG/WEBP instead of PNG; keep the basename (for example `screen-01.jpg`). Upload them by committing files to this repository. Use screenshots you own or have permission to use, and remove private information before committing.

Optional: add `canva-series/assets/logo.png` to brand the video.

## Edit the content

Edit `canva-series/storyboards/day01.json` before running. Each of its six scenes has a title, short on-screen caption, and narration. The default storyboard is an editable example for a first Canva mobile edit; replace the wording to match your actual screenshots.

## Run Day 1

1. Open **Actions → Canva Day 1 Video**.
2. Choose **Run workflow**.
3. Leave day number at `1` for the first video.
4. Download the `canva-day-01` artifact after the run succeeds.

The renderer creates a 720×1280 (9:16), 30-second H.264/AAC MP4 at `canva-series/output/day01.mp4`. It applies a slow Ken Burns movement to each screenshot, readable title/caption overlays, six short Edge-TTS narration segments, and a quiet generated audio bed. The MP4 is uploaded as an Actions artifact; it is not committed to the repository.

## Local run

Requires Python 3.11+, FFmpeg/FFprobe, and the repository requirements:

```bash
pip install -r requirements.txt
python canva-series/render_day.py --day 1
```

The first version is deliberately deterministic: storyboard copy and screenshots come from GitHub, so the same inputs can be reviewed and rerun. It does not operate Canva Mobile itself; it produces a polished MP4 for final optional trimming/polish in Canva.

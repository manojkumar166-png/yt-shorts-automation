# Tutorial video series — separate from the original Shorts pipeline

This folder contains an independent 30-second vertical video pipeline. The existing Shorts generator and its original workflow are intentionally left unchanged.

## Current 48-image series

The uploaded archive contains 48 numbered scenes about **Why Leaves Change Color**. The successful preparation run extracted all 48 images with zero unreadable files. They are kept in filename order and split into eight consecutive groups of six.

Eight editable storyboards live in `storyboards/leaf-color/day01.json` through `day08.json`. Each has six titles, captions, and narration beats. The renderer creates one 720×1280, 30 fps, 30-second MP4 per storyboard.

## Generate all eight videos

1. Open **Actions → Render All Leaf Color Tutorial Shorts**.
2. Select **Run workflow**.
3. Keep the preparation run ID at `41628877178` (or enter another successful preparation run ID).
4. Wait for the workflow to finish successfully.
5. Download the artifact named `why-leaves-change-color-8-shorts`. It contains `day01.mp4` through `day08.mp4`.

The workflow downloads the prepared image artifact, stages six scenes per day, renders all eight MP4s, validates each file, and uploads the finished set for 14 days.

## Existing renderer

`render_day.py` is reused without changing its behavior. The eight new storyboards and the batch workflow are additive. The original Shorts generator and original workflow are not modified.

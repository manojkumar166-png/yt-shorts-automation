#!/usr/bin/env python3
"""Render one 30-second vertical tutorial from GitHub-hosted screenshots."""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
STORYBOARDS = ROOT / "storyboards"
OUTPUT = ROOT / "output"
SUPPORTED = (".png", ".jpg", ".jpeg", ".webp")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, typeface, max_width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=typeface)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def locate_screenshot(day_dir: Path, basename: str) -> Path:
    for ext in SUPPORTED:
        candidate = day_dir / f"{basename}{ext}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Missing screenshot '{basename}'. Add {basename}.png (or .jpg/.jpeg/.webp) "
        f"to {day_dir.relative_to(ROOT.parent)} and commit it to GitHub."
    )


def make_scene(screenshot: Path, scene: dict, index: int, total: int, width: int, height: int, logo_path: Path | None, output: Path) -> None:
    # Branded dark gradient background, generated locally and deterministically.
    base = Image.new("RGB", (width, height), (12, 17, 32))
    pixels = base.load()
    for y in range(height):
        t = y / max(1, height - 1)
        color = (int(15 + 12*t), int(20 + 8*t), int(42 + 18*t))
        ImageDraw.Draw(base).line((0, y, width, y), fill=color)

    draw = ImageDraw.Draw(base)
    margin = 48
    if logo_path and logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((92, 92), Image.Resampling.LANCZOS)
            base.paste(logo, (margin, 38), logo)
        except Exception as exc:
            print(f"[brand] Ignoring unreadable logo: {exc}")

    small = font(22, True)
    draw.rounded_rectangle((width-170, 42, width-margin, 88), radius=20, fill=(39, 54, 83))
    draw.text((width-148, 53), f"STEP {index:02d}/{total:02d}", font=small, fill=(194, 214, 255))

    title_font = font(43, True)
    title_lines = wrap_text(draw, scene["title"].upper(), title_font, width - 2*margin)
    y = 142
    for line in title_lines[:2]:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255), stroke_width=1)
        y += 54

    # The source screenshot is shown in a clean rounded card, fully visible.
    card = (margin, 315, width-margin, 1010)
    card_w, card_h = card[2]-card[0], card[3]-card[1]
    source = Image.open(screenshot).convert("RGB")
    fitted = ImageOps.contain(source, (card_w-22, card_h-22), method=Image.Resampling.LANCZOS)
    panel = Image.new("RGB", (card_w, card_h), (245, 247, 251))
    panel.paste(fitted, ((card_w-fitted.width)//2, (card_h-fitted.height)//2))
    mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_w-1, card_h-1), radius=26, fill=255)
    base.paste(panel, (card[0], card[1]), mask)

    # Caption panel.
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((margin, 1050, width-margin, 1195), radius=24, fill=(29, 43, 68), outline=(74, 103, 151), width=2)
    cap_font = font(27, True)
    caption_lines = wrap_text(draw, scene["caption"], cap_font, width - 2*margin - 44)
    cy = 1080
    for line in caption_lines[:3]:
        draw.text((margin+24, cy), line, font=cap_font, fill=(241, 246, 255))
        cy += 34

    # Bottom progress indicator.
    bar_y = 1230
    draw.rounded_rectangle((margin, bar_y, width-margin, bar_y+8), radius=4, fill=(51, 65, 90))
    progress_x = margin + int((width-2*margin) * index / total)
    draw.rounded_rectangle((margin, bar_y, max(margin+8, progress_x), bar_y+8), radius=4, fill=(76, 153, 255))
    draw.text((margin, 1250), "30-SECOND MOBILE TUTORIAL", font=font(14, True), fill=(153, 170, 200))
    base.save(output, quality=94)


async def create_voiceover(scenes: list[dict], voice: str, output: Path) -> bool:
    try:
        import edge_tts
        with tempfile.TemporaryDirectory(prefix="canva-tts-") as temp:
            temp_dir = Path(temp)
            segments = []
            for index, scene in enumerate(scenes, start=1):
                part = temp_dir / f"voice-{index:02d}.mp3"
                communicate = edge_tts.Communicate(scene["narration"], voice, rate="-20%", volume="+0%")
                await communicate.save(str(part))
                # Preserve slower natural TTS pace; never speed narration up.
                fitted = temp_dir / f"voice-fit-{index:02d}.mp3"
                run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                     "-i", str(part), "-af", "apad=pad_dur=4.95,atrim=0:5",
                     "-c:a", "libmp3lame", "-q:a", "4", str(fitted)])
                segments.append(fitted)
            listing = temp_dir / "concat.txt"
            listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
            run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c:a", "libmp3lame", "-q:a", "4", str(output)])
        return True
    except Exception as exc:
        print(f"[audio] Edge-TTS unavailable; continuing with an instrumental audio bed only: {exc}")
        return False


def render(day: int) -> Path:
    storyboard_path = STORYBOARDS / f"day{day:02d}.json"
    if not storyboard_path.exists():
        raise FileNotFoundError(f"No storyboard found: {storyboard_path}")
    config = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = config.get("scenes", [])
    if len(scenes) != 6:
        raise ValueError("A 30-second storyboard must contain exactly six scenes.")
    width, height = int(config.get("width", 720)), int(config.get("height", 1280))
    duration, fps = int(config.get("duration_seconds", 30)), int(config.get("fps", 30))
    if (width, height) != (720, 1280) or duration != 30 or fps != 30:
        raise ValueError("This first version is fixed at 720x1280, 30 fps, and 30 seconds.")
    day_dir = ASSETS / f"day{day:02d}"
    logo = ASSETS / "logo.png"
    screenshots = [locate_screenshot(day_dir, scene.get("image", f"screen-{i:02d}")) for i, scene in enumerate(scenes, 1)]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="canva-render-") as temp:
        temp_dir = Path(temp)
        clips = []
        for index, (scene, screenshot) in enumerate(zip(scenes, screenshots), start=1):
            still = temp_dir / f"scene-{index:02d}.jpg"
            clip = temp_dir / f"clip-{index:02d}.mp4"
            make_scene(screenshot, scene, index, len(scenes), width, height, logo if logo.exists() else None, still)
            # Smooth Ken Burns motion with alternating horizontal drift.
            # Avoid fading each scene to black; keep the sequence continuous.
            direction = 1 if index % 2 else -1
            zoom = "min(zoom+0.0010,1.055)"
            drift = f"{direction}*on*0.16"
            run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-loop", "1", "-i", str(still), "-t", "5",
                "-vf", f"scale=800:1422,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)+({drift})':y='ih/2-(ih/zoom/2)':d=150:s=720x1280:fps=30,format=yuv420p",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", str(clip)
            ])
            clips.append(clip)

        concat_list = temp_dir / "clips.txt"
        concat_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
        silent_video = temp_dir / "silent.mp4"
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(silent_video)])

        voice_file = temp_dir / "voice.mp3"
        has_voice = asyncio.run(create_voiceover(scenes, config.get("voice", "en-US-AriaNeural"), voice_file))
        destination = OUTPUT / f"day{day:02d}.mp4"
        if has_voice:
            audio_filter = "[1:a]apad,atrim=0:30,volume=1.0[voice];[2:a]volume=0.035[music];[voice][music]amix=inputs=2:duration=longest:dropout_transition=0[a]"
            run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent_video), "-i", str(voice_file), "-f", "lavfi", "-i", "sine=frequency=174:sample_rate=44100:duration=30", "-filter_complex", audio_filter, "-map", "0:v:0", "-map", "[a]", "-t", "30", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(destination)])
        else:
            run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent_video), "-f", "lavfi", "-i", "sine=frequency=174:sample_rate=44100:duration=30", "-filter:a", "volume=0.035", "-map", "0:v:0", "-map", "1:a:0", "-t", "30", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(destination)])

    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_type", "-of", "json", str(destination)], check=True, capture_output=True, text=True)
    info = json.loads(probe.stdout)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    actual = float(info.get("format", {}).get("duration", 0))
    if not video or video.get("width") != width or video.get("height") != height or not audio or abs(actual-duration) > 0.4:
        raise RuntimeError(f"Output validation failed: {info}")
    if destination.stat().st_size < 80_000:
        raise RuntimeError("Output MP4 is unexpectedly small.")
    print(f"[success] {destination} — {width}x{height}, {actual:.2f}s, audio={audio}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.day <= 30:
        parser.error("--day must be between 1 and 30")
    render(args.day)

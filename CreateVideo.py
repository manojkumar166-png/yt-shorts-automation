import os
import platform
import random
import subprocess
from pathlib import Path

from moviepy.config import change_settings

if platform.system() == "Windows":
    change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.2-Q16-HDRI\\magick.exe"})
else:
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    CompositeAudioClip, ColorClip, concatenate_audioclips
)
from moviepy.video.fx.all import colorx, lum_contrast
from moviepy.audio.fx.all import audio_fadein, audio_fadeout, audio_normalize
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from proglog import ProgressBarLogger


class QuietMoviePyLogger(ProgressBarLogger):
    """Hide noisy progress updates but print one completed video-frame line."""
    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == "t" and attr == "index":
            total = self.bars.get(bar, {}).get("total")
            if total and value >= total:
                print(f"t: 100%|██████████| {value}/{total} frames complete", flush=True)

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

TARGET_W, TARGET_H = 1080, 1920
GAP = 0.2
TRANSITION_DURATION = 0.35
AUDIO_FADE_DURATION = 0.35
MUSIC_DIR = Path("assets/music")
SFX_DIR = Path("assets/sfx")


def _make_pil_text(text, fontsize=100):
    """Create a transparent, legible, two-line-safe caption image."""
    img = Image.new("RGBA", (TARGET_W - 100, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize
        )
    except Exception:
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", fontsize)
        except Exception:
            font = ImageFont.load_default()
    # Keep long words within the safe title area.
    while draw.textbbox((0, 0), text, font=font, stroke_width=7)[2] > img.width - 30 and fontsize > 48:
        fontsize -= 4
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
        except Exception:
            break
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=7)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (img.width - text_w) / 2, (img.height - text_h) / 2
    draw.rounded_rectangle((x - 24, y - 14, x + text_w + 24, y + text_h + 14),
                           radius=24, fill=(8, 12, 24, 155))
    draw.text((x, y), text, font=font, fill="white",
              stroke_width=7, stroke_fill=(0, 0, 0, 230))
    return np.array(img)


def _cinematic_image_clip(image_path, duration, start, motion_seed=0, transition="crossfade"):
    """Portrait crop, cinematic grade and restrained Ken Burns camera movement."""
    clip = ImageClip(image_path)
    scale = max(TARGET_W / clip.w, TARGET_H / clip.h) * 1.12
    clip = clip.resize(scale)
    rng = random.Random(motion_seed)
    direction_x, direction_y = rng.choice((-1, 1)), rng.choice((-1, 1))
    zoom_start, zoom_end = rng.uniform(1.02, 1.07), rng.uniform(1.13, 1.19)

    # MoviePy's get_frame() resolves self.make_frame dynamically. Saving a
    # bound get_frame method is therefore NOT safe: set_make_frame() mutates
    # the same clip and the saved method would call camera_frame recursively.
    # Snapshot the actual frame callable before installing our transformation.
    source_make_frame = clip.make_frame

    def camera_frame(t):
        progress = min(max(float(t) / max(float(duration), 0.001), 0.0), 1.0)
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        frame = source_make_frame(t)
        pil = Image.fromarray(np.asarray(frame).astype(np.uint8))
        target_w = max(TARGET_W, int(TARGET_W * zoom))
        target_h = max(TARGET_H, int(TARGET_H * zoom))
        pil = pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
        max_x, max_y = pil.width - TARGET_W, pil.height - TARGET_H
        offset_x = int(max_x * (0.5 + 0.22 * direction_x * progress))
        offset_y = int(max_y * (0.5 + 0.22 * direction_y * progress))
        offset_x = min(max(offset_x, 0), max_x)
        offset_y = min(max(offset_y, 0), max_y)
        return np.asarray(pil.crop((offset_x, offset_y, offset_x + TARGET_W, offset_y + TARGET_H)))

    clip = clip.set_make_frame(camera_frame).set_duration(duration)
    clip.size = (TARGET_W, TARGET_H)
    clip = colorx(clip, 1.06)
    clip = lum_contrast(clip, lum=0, contrast=0.12, contrast_thr=127)
    if transition == "dip":
        clip = clip.fadein(TRANSITION_DURATION).fadeout(TRANSITION_DURATION)
    elif transition == "fade":
        clip = clip.fadein(TRANSITION_DURATION)
    else:
        clip = clip.crossfadein(TRANSITION_DURATION)
    return clip.set_start(start)


def _audio_assets(directory):
    """Return local, user-provided audio assets only; no unlicensed downloads."""
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir()
                  if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"})


def _probe_video(path, expected_duration):
    """Fail the pipeline if FFprobe cannot verify a valid vertical MP4."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True
    )
    import json
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    duration = float(data.get("format", {}).get("duration", 0))
    if not video or (video.get("width"), video.get("height")) != (TARGET_W, TARGET_H):
        raise RuntimeError("Quality check failed: output is not 1080x1920 video.")
    if not audio:
        raise RuntimeError("Quality check failed: rendered video has no audio stream.")
    if duration < 55 or duration > 90 or abs(duration - expected_duration) > 3:
        raise RuntimeError(f"Quality check failed: unexpected video duration {duration:.1f}s.")
    if Path(path).stat().st_size < 100_000:
        raise RuntimeError("Quality check failed: MP4 file is unexpectedly small.")
    print(f"  [Quality] PASS — {video['width']}x{video['height']}, {duration:.1f}s, audio present.")


def create_video(texts, audio_files, bg_images, output_path, topic=""):
    if len(texts) != 6 or len(bg_images) != 12:
        raise ValueError(f"Expected 6 narration scenes and 12 images; got {len(texts)} scenes and {len(bg_images)} images.")
    if len(audio_files) != len(texts):
        raise ValueError("Each narration scene must have exactly one audio file.")

    audio_clips = [AudioFileClip(p) for p in audio_files]
    if not audio_clips:
        raise ValueError("No narration audio clips were provided.")

    starts, t = [], 0.0
    speech_duration = sum(clip.duration for clip in audio_clips)
    for clip in audio_clips:
        starts.append(t)
        t += clip.duration + GAP
    total_duration = t + 0.5
    print(f"  [Duration] Narration {speech_duration:.1f}s; rendered video {total_duration:.1f}s (target approximately 70s).")

    # Normalize narration gently and retain clear voice priority.
    narration_layers = []
    for index, (audio_clip, start) in enumerate(zip(audio_clips, starts)):
        try:
            layer = audio_normalize(audio_clip)
        except Exception:
            layer = audio_clip
        if index > 0:
            layer = audio_fadein(layer, AUDIO_FADE_DURATION)
        if index == len(audio_clips) - 1:
            layer = audio_fadeout(layer, 0.6)
        narration_layers.append(layer.set_start(start))
    audio_layers = list(narration_layers)

    # Optional soundtrack: put a properly licensed/user-owned track in assets/music.
    # Music remains quiet under speech (automatic voice-priority ducking); fade edges.
    music_files = _audio_assets(MUSIC_DIR)
    if music_files:
        music = AudioFileClip(str(music_files[0]))
        if music.duration < total_duration:
            loops = int(total_duration // music.duration) + 1
            music = concatenate_audioclips([music] * loops)
        music = music.subclip(0, total_duration)
        music = audio_fadein(audio_fadeout(music, 1.2), 1.0).volumex(0.10)
        audio_layers.append(music.set_start(0))
        print(f"  [Music] Using local track {music_files[0].name}; voice-priority mix at 10%.")

    # Optional local sound effects, placed at scene boundaries and kept subtle.
    sfx_files = _audio_assets(SFX_DIR)
    sfx_clips = []
    if sfx_files:
        for index, start in enumerate(starts[1:], start=1):
            fx_path = sfx_files[(index - 1) % len(sfx_files)]
            fx = AudioFileClip(str(fx_path))
            if fx.duration > 1.8:
                fx = fx.subclip(0, 1.8)
            fx = audio_fadein(audio_fadeout(fx, min(0.35, fx.duration / 3)), min(0.08, fx.duration / 3)).volumex(0.16)
            sfx_clips.append(fx.set_start(max(0, start - 0.12)))
        audio_layers.extend(sfx_clips)
        print(f"  [SFX] Added {len(sfx_clips)} subtle transition effects from assets/sfx.")

    final_audio = CompositeAudioClip(audio_layers).set_duration(total_duration)

    bg_clips = []
    for scene_index, audio_clip in enumerate(audio_clips):
        print(f"  [Render] Preparing scene {scene_index + 1}/{len(audio_clips)} (2 images)...", flush=True)
        scene_duration = audio_clip.duration + GAP + (0.5 if scene_index == len(audio_clips) - 1 else 0)
        view_duration = scene_duration / 2
        for view_index in range(2):
            image_index = scene_index * 2 + view_index
            transition = "dip" if (scene_index + view_index) % 4 == 3 else "crossfade"
            bg_clips.append(_cinematic_image_clip(
                bg_images[image_index], view_duration,
                starts[scene_index] + view_index * view_duration,
                motion_seed=scene_index * 17 + view_index, transition=transition
            ))

    grain_rng = np.random.default_rng(21)
    grain = grain_rng.normal(128, 13, (TARGET_H, TARGET_W)).clip(0, 255).astype(np.uint8)
    grain_clip = ImageClip(np.stack([grain] * 3, axis=-1)).set_duration(total_duration).set_opacity(0.025)
    yy, xx = np.ogrid[:TARGET_H, :TARGET_W]
    distance = np.sqrt((xx - TARGET_W / 2) ** 2 + (yy - TARGET_H / 2) ** 2)
    vignette = (np.clip(distance / (TARGET_W * 0.72), 0, 1) * 105).astype(np.uint8)
    vignette_clip = ImageClip(np.stack([vignette] * 3, axis=-1)).set_duration(total_duration).set_opacity(0.35)

    print("  [Captions] Loading tiny speech model (first run may download it)...", flush=True)
    overlays = []
    if HAS_WHISPER:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("  [Captions] Model ready; transcribing narration with word timestamps...", flush=True)
        for audio_index, (audio_file, start_time) in enumerate(zip(audio_files, starts), start=1):
            print(f"  [Captions] Transcribing voice {audio_index}/{len(audio_files)}...", flush=True)
            segments, _ = model.transcribe(audio_file, word_timestamps=True)
            for segment in segments:
                for word in segment.words:
                    word_start = start_time + word.start
                    word_duration = max(word.end - word.start, 0.1)
                    word_text = word.word.strip().upper()
                    if not word_text:
                        continue
                    text_img = _make_pil_text(word_text, 100)
                    overlays.append(
                        ImageClip(text_img).set_duration(word_duration).set_start(word_start)
                        .set_position(("center", 1320))
                        .resize(lambda elapsed: 1.04 if elapsed < 0.08 else 1.0)
                        .fadein(0.05).fadeout(0.06)
                    )
    else:
        print("  [Captions] faster-whisper unavailable; captions skipped.")

    print("  [Render] Compositing 1080x1920 frames at 30 fps...", flush=True)
    final = CompositeVideoClip(
        bg_clips + [grain_clip, vignette_clip] + overlays,
        size=(TARGET_W, TARGET_H)
    ).set_duration(total_duration).set_audio(final_audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        final.write_videofile(
            output_path, fps=30, codec="libx264", audio_codec="aac",
            preset="veryfast", bitrate="6000k", threads=4,
            ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
            logger=QuietMoviePyLogger(),  # Show only the final frame-complete line; hide chunk/intermediate bars.
        )
        print("Moviepy - Done !", flush=True)
        print(f"Moviepy - video ready {output_path}", flush=True)
        print("  [Quality] Checking MP4 streams and duration...", flush=True)
        _probe_video(output_path, total_duration)
    finally:
        final.close()
        final_audio.close()
        for clip in audio_clips + sfx_clips:
            try:
                clip.close()
            except Exception:
                pass
        for clip in narration_layers:
            try:
                clip.close()
            except Exception:
                pass
        if "music" in locals():
            music.close()
    return output_path

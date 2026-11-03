import os
import platform
import random

from moviepy.config import change_settings

if platform.system() == "Windows":
    change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.2-Q16-HDRI\\magick.exe"})
else:
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    CompositeAudioClip, ColorClip
)
from moviepy.video.fx.all import colorx, lum_contrast
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

TARGET_W, TARGET_H = 1080, 1920
GAP = 0.2
TRANSITION_DURATION = 0.35
AUDIO_FADE_DURATION = 0.35


def _make_pil_text(text, fontsize=110):
    """Create a transparent, high-contrast subtitle word image."""
    img = Image.new("RGBA", (TARGET_W, 400), (0, 0, 0, 0))
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

    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=8)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (TARGET_W - text_w) / 2, (400 - text_h) / 2
    draw.text(
        (x, y), text, font=font, fill="white",
        stroke_width=8, stroke_fill=(0, 0, 0, 255)
    )
    return np.array(img)


def _cinematic_image_clip(image_path, duration, start, motion_seed=0, transition="crossfade"):
    """Portrait crop, cinematic grade and restrained Ken Burns camera movement."""
    clip = ImageClip(image_path)
    scale = max(TARGET_W / clip.w, TARGET_H / clip.h) * 1.12
    clip = clip.resize(scale)

    # Slightly oversized source gives room for a moving camera crop.
    crop_w, crop_h = clip.w, clip.h
    rng = random.Random(motion_seed)
    direction_x = rng.choice((-1, 1))
    direction_y = rng.choice((-1, 1))
    zoom_start = rng.uniform(1.02, 1.07)
    zoom_end = rng.uniform(1.13, 1.19)

    def camera_frame(t):
        progress = min(max(t / max(duration, 0.001), 0.0), 1.0)
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        frame = clip.get_frame(t)
        h, w = frame.shape[:2]
        target_w, target_h = int(TARGET_W * zoom), int(TARGET_H * zoom)
        # Resize each frame to create a smooth, editor-style push-in.
        from PIL import Image as PILImage
        pil = PILImage.fromarray(frame)
        pil = pil.resize((max(target_w, TARGET_W), max(target_h, TARGET_H)), PILImage.Resampling.LANCZOS)
        max_x, max_y = pil.width - TARGET_W, pil.height - TARGET_H
        offset_x = int(max_x * (0.5 + 0.22 * direction_x * progress))
        offset_y = int(max_y * (0.5 + 0.22 * direction_y * progress))
        return np.asarray(pil.crop((offset_x, offset_y, offset_x + TARGET_W, offset_y + TARGET_H)))

    clip = clip.set_make_frame(camera_frame).set_duration(duration)
    clip.size = (TARGET_W, TARGET_H)
    # Rich but restrained contrast/saturation for a cinematic social-video look.
    clip = colorx(clip, 1.08)
    clip = lum_contrast(clip, lum=0, contrast=0.16, contrast_thr=127)
    if transition == "dip":
        clip = clip.fadein(TRANSITION_DURATION).fadeout(TRANSITION_DURATION)
    elif transition == "fade":
        clip = clip.fadein(TRANSITION_DURATION)
    else:
        clip = clip.crossfadein(TRANSITION_DURATION)
    return clip.set_start(start)


def create_video(texts, audio_files, bg_images, output_path, topic=""):
    audio_clips = [AudioFileClip(p) for p in audio_files]
    if not audio_clips:
        raise ValueError("No narration audio clips were provided.")

    starts, t = [], 0.0
    speech_duration = sum(clip.duration for clip in audio_clips)
    for clip in audio_clips:
        starts.append(t)
        t += clip.duration + GAP
    total_duration = t + 0.5
    print(
        f"  [Duration] Narration {speech_duration:.1f}s; "
        f"rendered video {total_duration:.1f}s (target approximately 70s)."
    )

    # Smooth narration joins and gentle ending fade; no added music that could
    # compete with voiceover or introduce licensing problems.
    audio_layers = []
    for index, (audio_clip, start) in enumerate(zip(audio_clips, starts)):
        layer = audio_clip
        if index > 0:
            layer = layer.audio_fadein(AUDIO_FADE_DURATION)
        if index == len(audio_clips) - 1:
            layer = layer.audio_fadeout(AUDIO_FADE_DURATION)
        audio_layers.append(layer.set_start(start))
    final_audio = CompositeAudioClip(audio_layers).set_duration(total_duration)

    bg_clips = []
    images_per_scene = 2
    for scene_index, audio_clip in enumerate(audio_clips):
        scene_duration = audio_clip.duration + GAP
        if scene_index == len(audio_clips) - 1:
            scene_duration += 0.5
        first_image_index = scene_index * images_per_scene
        view_duration = scene_duration / images_per_scene
        for view_index in range(images_per_scene):
            image_index = first_image_index + view_index
            if image_index >= len(bg_images):
                continue
            # Alternate soft cross-dissolves with brief dip transitions.
            transition = "dip" if (scene_index + view_index) % 4 == 3 else "crossfade"
            clip = _cinematic_image_clip(
                bg_images[image_index],
                view_duration,
                starts[scene_index] + view_index * view_duration,
                motion_seed=scene_index * 17 + view_index,
                transition=transition,
            )
            bg_clips.append(clip)

        if not any(c.start >= starts[scene_index] and c.start < starts[scene_index] + scene_duration for c in bg_clips):
            bg_clips.append(
                ColorClip((TARGET_W, TARGET_H), color=(10, 12, 30), duration=scene_duration)
                .set_start(starts[scene_index])
            )

    # Subtle film grain texture adds depth without obscuring the visuals.
    grain_rng = np.random.default_rng(21)
    grain = grain_rng.normal(128, 13, (TARGET_H, TARGET_W)).clip(0, 255).astype(np.uint8)
    grain_rgb = np.stack([grain, grain, grain], axis=-1)
    grain_clip = (
        ImageClip(grain_rgb)
        .set_duration(total_duration)
        .set_opacity(0.035)
    )

    # Soft vignette draws attention toward the center of the vertical frame.
    yy, xx = np.ogrid[:TARGET_H, :TARGET_W]
    distance = np.sqrt((xx - TARGET_W / 2) ** 2 + (yy - TARGET_H / 2) ** 2)
    vignette = (np.clip(distance / (TARGET_W * 0.72), 0, 1) * 105).astype(np.uint8)
    vignette_rgb = np.stack([vignette] * 3, axis=-1)
    vignette_clip = ImageClip(vignette_rgb).set_duration(total_duration).set_opacity(0.42)

    print("  Building word-synced animated subtitles...")
    overlays = []
    if HAS_WHISPER:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        for audio_file, start_time in zip(audio_files, starts):
            segments, _ = model.transcribe(audio_file, word_timestamps=True)
            for segment in segments:
                for word in segment.words:
                    word_start = start_time + word.start
                    word_duration = max(word.end - word.start, 0.1)
                    word_text = word.word.strip().upper()
                    if not word_text:
                        continue
                    text_img = _make_pil_text(word_text, 110)
                    subtitle = (
                        ImageClip(text_img)
                        .set_duration(word_duration)
                        .set_start(word_start)
                        .set_position(("center", 1350))
                        .resize(lambda elapsed: 1.07 if elapsed < 0.07 else 1.0)
                        .fadein(0.05)
                        .fadeout(0.06)
                    )
                    overlays.append(subtitle)

    print("  Compositing cinematic video...")
    final = CompositeVideoClip(
        bg_clips + [grain_clip, vignette_clip] + overlays,
        size=(TARGET_W, TARGET_H)
    ).set_duration(total_duration)
    final = final.set_audio(final_audio)

    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="8000k",
        threads=4,
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger=None,
    )

    final.close()
    final_audio.close()
    for clip in audio_clips:
        clip.close()
    return output_path

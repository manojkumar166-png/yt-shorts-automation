"""Vertical 1080x1920 video with text overlays + voiceover."""
import os
import random
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ColorClip, CompositeAudioClip,
)

TARGET_W, TARGET_H = 1080, 1920
GAP = 0.4


def _pick_background():
    os.makedirs("background", exist_ok=True)
    files = [
        os.path.join("background", f)
        for f in os.listdir("background")
        if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))
    ]
    return random.choice(files) if files else None


def _safe_textclip(text, size, **extra):
    common = dict(fontsize=size, color="white", method="caption",
                  size=(900, None), align="center",
                  stroke_color="black", stroke_width=3)
    common.update(extra)
    for font in ("DejaVu-Sans-Bold", "Arial-Bold", "Arial"):
        try:
            return TextClip(text, font=font, **common)
        except Exception:
            continue
    return TextClip(text, **common)


def create_video(texts, audio_files, output_path, topic=""):
    audio_clips = [AudioFileClip(p) for p in audio_files]

    starts, t = [], 0.0
    for clip in audio_clips:
        starts.append(t)
        t += clip.duration + GAP
    total = t + 0.5

    final_audio = CompositeAudioClip(
        [c.set_start(s) for c, s in zip(audio_clips, starts)]
    ).set_duration(total)

    bg = _pick_background()
    if bg:
        print(f"  background: {os.path.basename(bg)}")
        base = VideoFileClip(bg)
        video = base.subclip(0, min(total, base.duration))
        video = video.resize(height=TARGET_H)
        if video.w < TARGET_W:
            video = video.resize(width=TARGET_W)
        video = video.crop(x_center=video.w/2, y_center=video.h/2,
                           width=TARGET_W, height=TARGET_H)
    else:
        print("  background: solid color (add .mp4 to /background)")
        video = ColorClip((TARGET_W, TARGET_H), color=(10, 12, 30), duration=total)
    video = video.set_audio(final_audio)

    overlays = []
    for text, clip, start in zip(texts, audio_clips, starts):
        tc = (_safe_textclip(text, 72)
              .set_duration(clip.duration)
              .set_start(start)
              .set_position(("center", 950)))
        overlays.append(tc)

    if topic:
        title = (_safe_textclip(topic.upper(), 58, color="yellow", method="label")
                 .set_duration(min(3, total))
                 .set_position(("center", 220)))
        overlays.append(title)

    final = CompositeVideoClip([video] + overlays).set_duration(total)
    final.write_videofile(output_path, fps=24, codec="libx264",
                          audio_codec="aac", preset="medium", threads=4, logger="bar")

    video.close()
    for c in audio_clips:
        c.close()
    return output_path
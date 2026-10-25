"""Vertical 1080x1920 video with HD images and perfectly synced white subtitles."""
import os
import platform
from moviepy.config import change_settings

if platform.system() == "Windows":
    change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})
else:
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

from moviepy.editor import (
    ImageClip, AudioFileClip, TextClip, CompositeVideoClip,
    CompositeAudioClip, ColorClip
)

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

TARGET_W, TARGET_H = 1080, 1920
GAP = 0.3

def _safe_textclip(text, size, color="white", **extra):
    # Balanced stroke width (5) so it outlines the text without swallowing it
    common = dict(fontsize=size, color=color, font="DejaVu-Sans-Bold",
                  method="caption", size=(980, None), align="center",
                  stroke_color="black", stroke_width=5) 
    common.update(extra)
    try:
        return TextClip(text, **common)
    except:
        common["font"] = "Arial-Bold"
        return TextClip(text, **common)

def create_video(texts, audio_files, bg_images, output_path, topic=""):
    audio_clips = [AudioFileClip(p) for p in audio_files]

    starts, t = [], 0.0
    for clip in audio_clips:
        starts.append(t)
        t += clip.duration + GAP
    total_duration = t + 0.5

    final_audio = CompositeAudioClip(
        [c.set_start(s) for c, s in zip(audio_clips, starts)]
    ).set_duration(total_duration)

    bg_clips = []
    for i, audio_clip in enumerate(audio_clips):
        dur = audio_clip.duration + GAP
        
        if i < len(bg_images):
            bg_img = bg_images[i]
            clip = ImageClip(bg_img)
            
            w_ratio = TARGET_W / clip.w
            h_ratio = TARGET_H / clip.h
            scale = max(w_ratio, h_ratio)
            
            clip = clip.resize(scale)
            clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_W, height=TARGET_H)
            clip = clip.set_duration(dur)
            clip = clip.resize(lambda t: 1 + 0.05 * t) 
        else:
            clip = ColorClip((TARGET_W, TARGET_H), color=(10, 12, 30), duration=dur)
            
        clip = clip.set_start(starts[i])
        bg_clips.append(clip)

    print("  Building perfectly synced subtitles...")
    overlays = []
    
    if HAS_WHISPER:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        
        for i, (audio_file, start_time) in enumerate(zip(audio_files, starts)):
            segments, _ = model.transcribe(audio_file, word_timestamps=True)
            
            for segment in segments:
                for word in segment.words:
                    w_start = start_time + word.start
                    w_dur = word.end - word.start
                    
                    if w_dur < 0.1: w_dur = 0.1 
                    word_text = word.word.strip().upper()
                    if not word_text: continue
                    
                    # Use pure white text
                    tc = (_safe_textclip(word_text, 110, color="white")
                          .set_duration(w_dur)
                          .set_start(w_start)
                          .set_position(("center", 960)))
                    overlays.append(tc)
    else:
        for text, clip, start_time in zip(texts, audio_clips, starts):
            words = text.split()
            chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
            chunk_dur = clip.duration / len(chunks)
            for i, chunk in enumerate(chunks):
                w_start = start_time + (i * chunk_dur)
                tc = (_safe_textclip(chunk.upper(), 110, color="white")
                      .set_duration(chunk_dur)
                      .set_start(w_start)
                      .set_position(("center", 960)))
                overlays.append(tc)

    if topic:
        title = (_safe_textclip(topic.upper(), 70, color="yellow", method="label")
                 .set_duration(min(3, total_duration))
                 .set_position(("center", 250)))
        overlays.append(title)

    print("  Compositing video...")
    final = CompositeVideoClip(bg_clips + overlays).set_duration(total_duration)
    final = final.set_audio(final_audio)

    final.write_videofile(output_path, fps=30, codec="libx264",
                          audio_codec="aac", preset="slow", bitrate="8000k", threads=4, 
                          ffmpeg_params=["-pix_fmt", "yuv420p"], logger="bar")

    for c in audio_clips:
        c.close()
    return output_path
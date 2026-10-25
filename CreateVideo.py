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
from moviepy.video.fx.all import colorx, lum_contrast
from moviepy.audio.fx.all import audio_loop
import numpy as np
import random

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

TARGET_W, TARGET_H = 1080, 1920
GAP = 0.2

EMOJI_MAP = {
    "space": "🚀", "black hole": "🌌", "galaxy": "🌌", "star": "⭐", "universe": "🌌",
    "cat": "🐱", "dog": "🐶", "animal": "🐾",
    "ocean": "🌊", "water": "💧", "fish": "🐟", "shark": "🦈",
    "history": "📜", "ancient": "🏛️", "rome": "🏛️", "egypt": "🐪", "war": "⚔️",
    "brain": "🧠", "psychology": "🧠", "mind": "🧠",
    "money": "💰", "rich": "💸", "business": "📈",
    "fire": "🔥", "danger": "⚠️", "death": "💀", "secret": "🤫",
    "earth": "🌍", "nature": "🌿", "tree": "🌳", "mountain": "⛰️"
}

def get_emoji_for_topic(topic):
    topic = topic.lower()
    for key, emoji in EMOJI_MAP.items():
        if key in topic:
            return emoji
    return "🔥"

def _safe_textclip(text, size, color="white", **extra):
    common = dict(fontsize=size, color=color, font="DejaVu-Sans-Bold",
                  method="caption", size=(980, None), align="center",
                  stroke_color="black", stroke_width=8) 
    common.update(extra)
    try:
        return TextClip(text, **common)
    except:
        common["font"] = "Arial-Bold"
        return TextClip(text, **common)

def create_video(texts, audio_files, bg_images, output_path, topic=""):
    audio_clips = [AudioFileClip(p) for p in audio_files]
    topic_emoji = get_emoji_for_topic(topic)

    starts, t = [], 0.0
    for clip in audio_clips:
        starts.append(t)
        t += clip.duration + GAP
    total_duration = t + 0.5

    # 1. AUDIO MIXING
    voice_track = CompositeAudioClip([c.set_start(s) for c, s in zip(audio_clips, starts)])
    audio_layers = [voice_track]
    
    if os.path.exists("bg_music.mp3"):
        print("  [Mix] Adding background music...")
        bg_music = AudioFileClip("bg_music.mp3")
        bg_music = audio_loop(bg_music, duration=total_duration).volumex(0.15)
        audio_layers.append(bg_music)
        
    if os.path.exists("whoosh.mp3"):
        print("  [Mix] Adding whoosh effects...")
        whoosh = AudioFileClip("whoosh.mp3").volumex(0.5)
        whooshes = []
        for i, start in enumerate(starts):
            if i > 0:
                whooshes.append(whoosh.set_start(start))
        if whooshes:
            audio_layers.append(CompositeAudioClip(whooshes))

    final_audio = CompositeAudioClip(audio_layers).set_duration(total_duration)

    # 2. BACKGROUND CLIPS
    bg_clips = []
    for i, audio_clip in enumerate(audio_clips):
        dur = audio_clip.duration + GAP
        if i == len(audio_clips) - 1:
            dur += 0.5
            
        if i < len(bg_images):
            clip = ImageClip(bg_images[i])
            w_ratio = TARGET_W / clip.w
            h_ratio = TARGET_H / clip.h
            scale = max(w_ratio, h_ratio) * 1.1 
            clip = clip.resize(scale)
            clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_W, height=TARGET_H)
            clip = colorx(clip, 1.2)
            clip = lum_contrast(clip, contrast=0.2)
            clip = clip.set_duration(dur)
            clip = clip.resize(lambda t: 1 + (0.12 * (t / dur) ** 0.5))
            
            def shake_position(t):
                if t < 0.15:
                    return (random.randint(-8, 8), random.randint(-8, 8))
                return ("center", "center")
            clip = clip.set_position(shake_position)
            
            if i > 0:
                clip = clip.crossfadein(0.3)
                overlap_start = max(0, starts[i] - 0.15)
            else:
                overlap_start = 0
            clip = clip.set_start(overlap_start)
        else:
            clip = ColorClip((TARGET_W, TARGET_H), color=(10, 12, 30), duration=dur)
            clip = clip.set_start(starts[i])
        bg_clips.append(clip)

    # 3. VIGNETTE
    vignette_array = np.zeros((TARGET_H, TARGET_W))
    for y in range(TARGET_H):
        for x in range(TARGET_W):
            dist = np.sqrt((x - TARGET_W/2)**2 + (y - TARGET_H/2)**2)
            vignette_array[y, x] = min(dist / (TARGET_W * 0.6), 1.0) * 120
    vignette_img = np.stack([vignette_array]*3, axis=-1).astype(np.uint8)
    vignette_clip = ImageClip(vignette_img).set_duration(total_duration).set_opacity(0.5)

    # 4. SUBTITLES WITH EMOJIS ON EVERY SCENE
    print("  Building perfectly synced subtitles...")
    overlays = []
    
    if HAS_WHISPER:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        
        for i, (audio_file, start_time) in enumerate(zip(audio_files, starts)):
            segments, _ = model.transcribe(audio_file, word_timestamps=True)
            
            # We track if we've added the emoji to this specific scene yet
            emoji_added = False
            
            for segment in segments:
                for word in segment.words:
                    w_start = start_time + word.start
                    w_dur = word.end - word.start
                    
                    if w_dur < 0.1: w_dur = 0.1 
                    word_text = word.word.strip().upper()
                    if not word_text: continue
                    
                    # Add emoji to the first word of the audio file
                    if not emoji_added:
                        word_text = f"{word_text} {topic_emoji}"
                        emoji_added = True
                    
                    def make_scale(t):
                        if t < 0.08:
                            return 1.08 - (t * 1.0)
                        return 1.0
                        
                    tc = (_safe_textclip(word_text, 115, color="white")
                          .set_duration(w_dur)
                          .set_start(w_start)
                          .set_position(("center", 1450)))
                    
                    tc = tc.resize(make_scale)
                    overlays.append(tc)

    print("  Compositing video...")
    final = CompositeVideoClip(bg_clips + [vignette_clip] + overlays, size=(TARGET_W, TARGET_H)).set_duration(total_duration)
    final = final.set_audio(final_audio)

    final.write_videofile(output_path, fps=30, codec="libx264",
                          audio_codec="aac", preset="medium", bitrate="8000k", threads=4, 
                          ffmpeg_params=["-pix_fmt", "yuv420p"], logger="bar")

    for c in audio_clips:
        c.close()
    return output_path
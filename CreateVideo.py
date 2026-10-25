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
import numpy as np

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

TARGET_W, TARGET_H = 1080, 1920
GAP = 0.2

def _safe_textclip(text, size, color="white", **extra):
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
            clip = ImageClip(bg_images[i])
            
            # 1. Make the image MASSIVE (2.5x the screen size)
            massive_w = int(TARGET_W * 2.5)
            massive_h = int(TARGET_H * 2.5)
            
            # 2. Scale the image to cover this massive area
            w_ratio = massive_w / clip.w
            h_ratio = massive_h / clip.h
            scale = max(w_ratio, h_ratio)
            clip = clip.resize(scale)
            clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=massive_w, height=massive_h)
            clip = clip.set_duration(dur)
            
            # 3. Create the camera movement function
            # The camera starts in the middle and moves, but the image is so big it never shows the edge.
            def make_camera_move(duration, index):
                def pos(t):
                    # Center coordinates of the massive image
                    center_x = massive_w / 2 - TARGET_W / 2
                    center_y = massive_h / 2 - TARGET_H / 2
                    
                    if index % 4 == 0:
                        # Zoom in (handled by resize below)
                        return (center_x, center_y)
                    elif index % 4 == 1:
                        # Zoom out (handled by resize below)
                        return (center_x, center_y)
                    elif index % 4 == 2:
                        # Pan Left to Right
                        return (center_x - (massive_w - TARGET_W) / 2 + (massive_w - TARGET_W) * (t / duration), center_y)
                    elif index % 4 == 3:
                        # Pan Right to Left
                        return (center_x + (massive_w - TARGET_W) / 2 - (massive_w - TARGET_W) * (t / duration), center_y)
                return pos

            # Apply pan
            clip = clip.set_position(make_camera_move(dur, i))
            
            # Apply zoom (if it's a zoom clip)
            if i % 4 == 0:
                clip = clip.resize(lambda t: 1 + 0.05 * t)
            elif i % 4 == 1:
                clip = clip.resize(lambda t: 1.05 - 0.05 * t)

            # Crop the moving camera window to the screen size
            clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_W, height=TARGET_H)
                
        else:
            clip = ColorClip((TARGET_W, TARGET_H), color=(10, 12, 30), duration=dur)
            
        clip = clip.set_start(starts[i])
        bg_clips.append(clip)

    # Add Vignette
    vignette_array = np.zeros((TARGET_H, TARGET_W))
    for y in range(TARGET_H):
        for x in range(TARGET_W):
            dist = np.sqrt((x - TARGET_W/2)**2 + (y - TARGET_H/2)**2)
            vignette_array[y, x] = min(dist / (TARGET_W * 0.7), 1.0) * 80
    vignette_img = np.stack([vignette_array]*3, axis=-1).astype(np.uint8)
    vignette_clip = ImageClip(vignette_img).set_duration(total_duration).set_opacity(0.4)

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
                    
                    color = "yellow" if i % 2 == 1 else "white"
                    
                    tc = (_safe_textclip(word_text, 110, color=color)
                          .set_duration(w_dur)
                          .set_start(w_start)
                          .set_position(("center", 960)))
                    overlays.append(tc)

    if topic:
        title = (_safe_textclip(topic.upper(), 70, color="white", method="label")
                 .set_duration(min(3, total_duration))
                 .set_position(("center", 250)))
        overlays.append(title)

    print("  Compositing video...")
    final = CompositeVideoClip(bg_clips + [vignette_clip] + overlays).set_duration(total_duration)
    final = final.set_audio(final_audio)

    final.write_videofile(output_path, fps=30, codec="libx264",
                          audio_codec="aac", preset="medium", bitrate="8000k", threads=4, 
                          ffmpeg_params=["-pix_fmt", "yuv420p"], logger="bar")

    for c in audio_clips:
        c.close()
    return output_path
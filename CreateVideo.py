import os
import platform
from moviepy.config import change_settings

if platform.system() == "Windows":
    change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})
else:
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    CompositeAudioClip, ColorClip
)
from moviepy.video.fx.all import colorx, lum_contrast
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

TARGET_W, TARGET_H = 1080, 1920
GAP = 0.2

def _make_pil_text(text, fontsize=110):
    # Create a transparent image for the text
    img = Image.new('RGBA', (TARGET_W, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to load a bold font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
    except:
        # Fallback to Windows font
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", fontsize)
        except:
            font = ImageFont.load_default()

    # Draw text with black stroke
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (TARGET_W - text_w) / 2
    y = (400 - text_h) / 2
    
    draw.text((x, y), text, font=font, fill="white", stroke_width=8, stroke_fill="black")
    return np.array(img)

def create_video(texts, audio_files, bg_images, output_path, topic=""):
    audio_clips = [AudioFileClip(p) for p in audio_files]

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

    final_audio = CompositeAudioClip(
        [c.set_start(s) for c, s in zip(audio_clips, starts)]
    ).set_duration(total_duration)

    bg_clips = []
    images_per_scene = 2
    for i, audio_clip in enumerate(audio_clips):
        dur = audio_clip.duration + GAP
        if i == len(audio_clips) - 1:
            dur += 0.5
            
        scene_clips = []
        first_image_index = i * images_per_scene
        view_duration = dur / images_per_scene
        for view in range(images_per_scene):
            image_index = first_image_index + view
            if image_index >= len(bg_images):
                continue
            clip = ImageClip(bg_images[image_index])
            w_ratio = TARGET_W / clip.w
            h_ratio = TARGET_H / clip.h
            scale = max(w_ratio, h_ratio) * 1.1
            clip = clip.resize(scale)
            clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_W, height=TARGET_H)
            clip = colorx(clip, 1.2)
            clip = lum_contrast(clip, contrast=0.2)
            clip = clip.set_duration(view_duration)
            clip = clip.resize(lambda t, d=view_duration: 1 + (0.12 * (t / d) ** 0.5))
            clip = clip.set_start(starts[i] + view * view_duration)
            if i > 0 or view > 0:
                clip = clip.crossfadein(0.2)
            scene_clips.append(clip)
        if not scene_clips:
            scene_clips.append(ColorClip((TARGET_W, TARGET_H), color=(10, 12, 30), duration=dur).set_start(starts[i]))
        bg_clips.extend(scene_clips)

    vignette_array = np.zeros((TARGET_H, TARGET_W))
    for y in range(TARGET_H):
        for x in range(TARGET_W):
            dist = np.sqrt((x - TARGET_W/2)**2 + (y - TARGET_H/2)**2)
            vignette_array[y, x] = min(dist / (TARGET_W * 0.6), 1.0) * 120
    vignette_img = np.stack([vignette_array]*3, axis=-1).astype(np.uint8)
    vignette_clip = ImageClip(vignette_img).set_duration(total_duration).set_opacity(0.5)

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
                    
                    # Create the text using Pillow
                    text_img = _make_pil_text(word_text, 110)
                    
                    def make_scale(t):
                        if t < 0.08:
                            return 1.08 - (t * 1.0)
                        return 1.0
                        
                    tc = (ImageClip(text_img)
                          .set_duration(w_dur)
                          .set_start(w_start)
                          .set_position(("center", 1350)))
                    
                    tc = tc.resize(make_scale)
                    overlays.append(tc)

    print("  Compositing video...")
    final = CompositeVideoClip(bg_clips + [vignette_clip] + overlays, size=(TARGET_W, TARGET_H)).set_duration(total_duration)
    final = final.set_audio(final_audio)

    final.write_videofile(output_path, fps=30, codec="libx264",
                          audio_codec="aac", preset="medium", bitrate="8000k", threads=4, 
                          ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)

    for c in audio_clips:
        c.close()
    return output_path
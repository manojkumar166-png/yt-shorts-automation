"""
CreateVideo.py - Modern MoviePy version
Creates vertical 9:16 video with text overlay and audio
No YouTube upload code
"""

import os
import random
from moviepy.editor import (
    VideoFileClip, AudioFileClip, 
    TextClip, CompositeVideoClip, 
    concatenate_audioclips, ColorClip
)

def get_background_video():
    """Get random background video from /background folder, or create solid color if not found"""
    bg_folder = "background"
    if os.path.exists(bg_folder):
        files = [f for f in os.listdir(bg_folder) if f.endswith(('.mp4', '.mov', '.avi'))]
        if files:
            return os.path.join(bg_folder, random.choice(files))
    
    # Fallback: create a gradient-like solid color video if no background
    print("  No background video found in /background - using solid color")
    return None

def create_video(texts, audio_files, output_path, topic=""):
    """
    texts: list of 3 facts
    audio_files: list of mp3 paths
    output_path: where to save final mp4
    """
    # Load audios and get total duration
    audio_clips = [AudioFileClip(a) for a in audio_files]
    total_duration = sum([a.duration for a in audio_clips])
    total_duration += 1.5 # padding

    # Add small silence between facts
    from moviepy.audio.AudioClip import CompositeAudioClip
    # Concatenate with small gaps
    current_time = 0
    positioned_audios = []
    for clip in audio_clips:
        positioned_audios.append(clip.set_start(current_time))
        current_time += clip.duration + 0.5
    
    final_audio = CompositeAudioClip(positioned_audios).set_duration(total_duration)

    # Background
    bg_path = get_background_video()
    if bg_path:
        video = VideoFileClip(bg_path).subclip(0, total_duration)
        # Make it vertical 9:16 - crop center
        w, h = video.size
        target_w, target_h = 1080, 1920
        # Resize to cover
        video = video.resize(height=target_h)
        # Crop width to 1080 centered
        video = video.crop(x_center=video.w/2, width=target_w, height=target_h)
    else:
        # Solid background
        video = ColorClip(size=(1080, 1920), color=(10, 10, 25), duration=total_duration)

    video = video.set_audio(final_audio)

    # Create text clips for each fact, timed with audio
    txt_clips = []
    current_time = 0
    for i, (text, audio_clip) in enumerate(zip(texts, audio_clips)):
        # Create text clip - modern moviepy uses method with TextClip
        try:
            txt = TextClip(
                text, 
                fontsize=70, 
                color='white', 
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(900, None),
                align='center'
            ).set_duration(audio_clip.duration).set_start(current_time).set_position(('center', 900))
        except:
            # Fallback without font specification
            txt = TextClip(
                text, 
                fontsize=60, 
                color='white',
                method='caption',
                size=(900, None)
            ).set_duration(audio_clip.duration).set_start(current_time).set_position(('center', 900))
        
        txt_clips.append(txt)
        current_time += audio_clip.duration + 0.5

    # Title clip for topic
    title = TextClip(
        topic.upper(), 
        fontsize=50, 
        color='yellow', 
        font='Arial-Bold',
        method='label'
    ).set_duration(2).set_position(('center', 200))

    final = CompositeVideoClip([video] + txt_clips + [title])
    final = final.set_duration(total_duration)

    # Write
    final.write_videofile(
        output_path, 
        fps=24, 
        codec='libx264', 
        audio_codec='aac',
        threads=4,
        logger='bar'
    )

    # Cleanup
    video.close()
    for c in audio_clips:
        c.close()

    return output_path

import asyncio 
import os 
import edge_tts 
from moviepy import AudioFileClip, ImageClip 
from PIL import Image 
 
def generate_script_lightweight(topic): 
    print(f"[*] Generating script for topic: {topic} (Lightweight Mode)...") 
    return f"Welcome! Today we are exploring the fascinating world of {topic}. Make sure to save this video and subscribe!" 
 
async def generate_voiceover(text, output_file="voiceover.mp3"): 
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural") 
    await communicate.save(output_file) 
 
def main(): 
    script = generate_script_lightweight("Productivity Hacks") 
    asyncio.run(generate_voiceover(script, "voiceover.mp3")) 
    audio = AudioFileClip("voiceover.mp3") 
    img = Image.new('RGB', (1080, 1920), color=(15, 23, 42)) 
    img.save("background.jpg") 
    video = ImageClip("background.jpg").with_duration(audio.duration).with_audio(audio) 
    video.write_videofile("youtube_ready.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2) 
    print("[+] Video successfully created: youtube_ready.mp4") 
 
if __name__ == "__main__": 
    main() 

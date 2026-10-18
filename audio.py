"""
audio.py - Free TTS version
Uses edge-tts (free, better than gTTS) with fallback to gTTS
"""

import os
import asyncio

async def _edge_tts_save(text, output_path):
    import edge_tts
    # Using good natural voice
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_path)

def generate_audios(texts):
    """
    texts: list of 3 facts
    returns: list of audio file paths
    """
    os.makedirs("audio", exist_ok=True)
    audio_files = []

    for i, text in enumerate(texts):
        output = f"audio/fact_{i}.mp3"
        try:
            # Try edge-tts first (free, better quality)
            asyncio.run(_edge_tts_save(text, output))
            print(f"  Created {output} with Edge-TTS")
        except Exception as e:
            print(f"  Edge-TTS failed ({e}), falling back to gTTS")
            try:
                from gtts import gTTS
                tts = gTTS(text=text, lang='en')
                tts.save(output)
            except Exception as e2:
                print(f"  gTTS also failed: {e2}")
                raise
        audio_files.append(output)

    return audio_files

if __name__ == "__main__":
    generate_audios(["Black holes are invisible.", "Time stops inside them.", "One could fit Earth inside."])

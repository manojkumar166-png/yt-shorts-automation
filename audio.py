"""Free TTS: Edge-TTS primary, gTTS fallback."""
import os
import asyncio


async def _edge_save(text, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="+10%")
    await communicate.save(path)


async def _edge_all(texts, paths):
    await asyncio.gather(*(_edge_save(t, p) for t, p in zip(texts, paths)))


def generate_audios(texts):
    os.makedirs("audio", exist_ok=True)
    paths = [os.path.join("audio", f"fact_{i}.mp3") for i in range(len(texts))]

    try:
        asyncio.run(_edge_all(texts, paths))
        print(f"  Edge-TTS OK ({len(paths)} files)")
        return paths
    except Exception as e:
        print(f"  Edge-TTS failed: {e} - falling back to gTTS")

    from gtts import gTTS
    for text, path in zip(texts, paths):
        gTTS(text=text, lang="en").save(path)
    print(f"  gTTS OK ({len(paths)} files)")
    return paths
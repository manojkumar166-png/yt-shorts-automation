"""
Colab Bootstrap — creates the full project from scratch.
Just upload this ONE file to Colab and run it.

Usage in Colab:
    from google.colab import files
    files.upload()          # upload colab_bootstrap.py
    exec(open("colab_bootstrap.py").read())
"""
import os

# ---- Create project folder structure ----
os.makedirs("project", exist_ok=True)
os.makedirs("project/background", exist_ok=True)
os.makedirs("project/audio", exist_ok=True)
os.makedirs("project/output", exist_ok=True)
os.chdir("project")

# ---- Write requirements.txt ----
with open("requirements.txt", "w") as f:
    f.write("""requests>=2.31.0
python-dotenv>=1.0.0
edge-tts>=6.1.9
gtts>=2.5.0
moviepy==1.0.3
pillow>=10.0.0
groq>=0.9.0
google-generativeai>=0.7.0
openai>=1.40.0
""")

# ---- Write audio.py ----
with open("audio.py", "w") as f:
    f.write('''"""Free TTS: Edge-TTS primary, gTTS fallback."""
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
''')

# ---- Write CreateVideo.py ----
with open("CreateVideo.py", "w") as f:
    f.write('''"""Vertical 1080x1920 video with text overlays + voiceover."""
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
''')

# ---- Write main.py ----
with open("main.py", "w") as f:
    f.write('''"""Automated YouTube Shorts generator.
Usage: python main.py "black holes"
Output: output/<topic>.mp4
"""
import os
import re
import sys


def generate_facts(topic):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    prompt = (f"You are a YouTube Shorts writer. Topic: {topic}. "
              f"Give exactly 3 surprising facts, 1 sentence each, max 20 words. "
              f"Return ONLY as a numbered list.")

    def _parse(txt):
        facts = []
        for line in txt.splitlines():
            line = line.strip()
            cleaned = re.sub(r"^\\s*(?:\\d+[\\.\\)\\-]|[\\-\\*])\\s*", "", line).strip()
            if len(cleaned) > 15:
                facts.append(cleaned)
        return facts[:3]

    if groq_key:
        try:
            print("  [Groq] generating...")
            from groq import Groq
            r = Groq(api_key=groq_key).chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85, max_tokens=300)
            facts = _parse(r.choices[0].message.content)
            if len(facts) >= 2:
                print(f"  [Groq] OK")
                return facts
        except Exception as e:
            print(f"  [Groq] failed: {e}")

    if gemini_key:
        try:
            print("  [Gemini] generating...")
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            m = genai.GenerativeModel("gemini-2.0-flash")
            facts = _parse(m.generate_content(prompt).text)
            if len(facts) >= 2:
                print(f"  [Gemini] OK")
                return facts
        except Exception as e:
            print(f"  [Gemini] failed: {e}")

    if openai_key:
        try:
            print("  [OpenAI] generating...")
            from openai import OpenAI
            r = OpenAI(api_key=openai_key).chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300)
            facts = _parse(r.choices[0].message.content)
            if len(facts) >= 2:
                print(f"  [OpenAI] OK")
                return facts
        except Exception as e:
            print(f"  [OpenAI] failed: {e}")

    print("  [OFFLINE] using built-in facts")
    return [
        f"{topic} is far stranger than most people realize.",
        f"Scientists discovered something about {topic} that changed everything.",
        f"The biggest myth about {topic} is completely wrong.",
    ]


def _slug(text):
    s = re.sub(r"[^\\w\\s-]", "", text).strip().lower()
    return re.sub(r"\\s+", "_", s)[:60] or "video"


def main():
    if len(sys.argv) < 2:
        print('Usage: python main.py "your topic"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    print(f"\\n=== YT Auto Generator ===")
    print(f"Topic: {topic}\\n")

    print("[1/3] Generating facts...")
    facts = generate_facts(topic)
    for i, f in enumerate(facts, 1):
        print(f"   {i}. {f}")

    print("\\n[2/3] Generating voiceovers...")
    from audio import generate_audios
    audio_files = generate_audios(facts)

    print("\\n[3/3] Rendering video...")
    from CreateVideo import create_video
    os.makedirs("output", exist_ok=True)
    out_path = os.path.join("output", f"{_slug(topic)}.mp4")
    create_video(facts, audio_files, out_path, topic)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\\nDONE -> {out_path}")
    print(f"  Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
''')

print("✅ Project files created in /content/project/")
print("   Files:", sorted(os.listdir(".")))
print("")
print("Next: run the install + generate cells.")
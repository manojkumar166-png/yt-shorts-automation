"""Automated YouTube Shorts generator.
Usage: python main.py "black holes"
Output: output/<topic>.mp4
"""
import os
import re
import sys


# --- Inline fact generator (Groq -> Gemini -> OpenAI -> offline) ---
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
            cleaned = re.sub(r"^\s*(?:\d+[\.\)\-]|[\-\*])\s*", "", line).strip()
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
# --- End inline generator ---


def _slug(text):
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"\s+", "_", s)[:60] or "video"


def main():
    if len(sys.argv) < 2:
        print('Usage: python main.py "your topic"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    print(f"\n=== YT Auto Generator ===")
    print(f"Topic: {topic}\n")

    print("[1/3] Generating facts...")
    facts = generate_facts(topic)
    for i, f in enumerate(facts, 1):
        print(f"   {i}. {f}")

    print("\n[2/3] Generating voiceovers...")
    from audio import generate_audios
    audio_files = generate_audios(facts)

    print("\n[3/3] Rendering video...")
    from CreateVideo import create_video
    os.makedirs("output", exist_ok=True)
    out_path = os.path.join("output", f"{_slug(topic)}.mp4")
    create_video(facts, audio_files, out_path, topic)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nDONE -> {out_path}")
    print(f"  Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
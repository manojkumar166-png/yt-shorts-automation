import os
import re
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def get_ai_script(topic):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("  [Script] No GEMINI_API_KEY found. Using offline fallback.")
        return None

    print("  [Script] Asking Gemini for a viral hook and script...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    prompt = f"""You are a viral YouTube Shorts writer. Topic: {topic}.
Return ONLY a valid JSON object (no markdown, no extra text) with exactly this format:
{{
  "hook": "A 1-sentence shocking opening hook (max 10 words)",
  "facts": ["Fact 1 (max 15 words)", "Fact 2", "Fact 3"],
  "image_queries": ["search query for fact 1", "search query for fact 2", "search query for fact 3"]
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
        print(f"  [Script] Hook: {data.get('hook')}")
        return data
    except Exception as e:
        print(f"  [Script] Gemini failed: {e}. Using fallback.")
        return None

def generate_facts(topic):
    ai_data = get_ai_script(topic)
    if ai_data and len(ai_data.get("facts", [])) >= 3:
        return ai_data
        
    print("  [Script] Using offline built-in facts.")
    return {
        "hook": f"Everything you know about {topic} is wrong...",
        "facts": [
            f"{topic} is far stranger than most people realize.",
            f"Scientists discovered something about {topic} that changed everything.",
            f"The biggest myth about {topic} is completely wrong."
        ],
        "image_queries": [topic, f"{topic} close up", f"{topic} space"]
    }

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

    print("[1/3] Generating script...")
    script_data = generate_facts(topic)
    
    full_script = [script_data["hook"]] + script_data["facts"]

    print("\n[2/3] Generating voiceovers...")
    from audio import generate_audios
    audio_files = generate_audios(full_script)

    print("\n[3/3] Fetching backgrounds & rendering video...")
    from fetch_background import get_background_images
    from CreateVideo import create_video
    
    image_queries = [topic] + script_data["image_queries"]
    bg_images = get_background_images(image_queries, num_images=4)
    
    os.makedirs("output", exist_ok=True)
    out_path = os.path.join("output", f"{_slug(topic)}.mp4")
    create_video(full_script, audio_files, bg_images, out_path, topic)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nDONE -> {out_path}")
    print(f"  Size: {size_mb:.1f} MB")

if __name__ == "__main__":
    main()
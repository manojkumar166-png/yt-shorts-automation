import os
import re
import sys
import json
import random
import requests
import tempfile
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOPICS_FILE = Path("topics.txt")
STATE_FILE = Path("state.json")
PER_DAY = 5
MAX_FAILS = 3

def load_topics():
    if not TOPICS_FILE.exists():
        return []
    lines = [l.strip() for l in TOPICS_FILE.read_text(encoding="utf-8").splitlines()]
    seen, out = set(), []
    for l in lines:
        if l and not l.startswith("#") and l not in seen:
            seen.add(l)
            out.append(l)
    return out

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"done": [], "failed": {}, "log": []}

def save_state(s):
    # Atomic write: never leaves a half-written file
    fd, tmp = tempfile.mkstemp(dir=".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)

def next_topic(topics, s):
    done = set(s["done"])
    for t in topics:
        if t not in done and s["failed"].get(t, 0) < MAX_FAILS:
            return t
    return None

def get_ai_script(topic):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    print("  [Script] Asking Gemini for a viral script...")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    
    prompt = f"""You are a viral YouTube Shorts writer. Topic: {topic}.
Return ONLY a valid JSON object (no markdown, no extra text) with exactly this format:
{{
  "hook": "A 1-sentence shocking opening hook (max 10 words)",
  "facts": ["Fact 1 (max 15 words)", "Fact 2", "Fact 3"],
  "image_queries": ["query 1", "query 2", "query 3", "query 4"]
}}"""

    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
        
        queries = data.get("image_queries", [])
        while len(queries) < 4:
            queries.append(topic)
        data["image_queries"] = queries[:4]
        return data
    except Exception as e:
        print(f"  [Script] Gemini failed: {e}")
        return None

def generate_video(topic):
    script_data = get_ai_script(topic)
    if not script_data:
        # Fallback if AI fails entirely
        script_data = {
            "hook": f"Everything you know about {topic} is wrong...",
            "facts": [
                f"{topic} is far stranger than most people realize.",
                f"Scientists discovered something about {topic} that changed everything.",
                f"The biggest myth about {topic} is completely wrong."
            ],
            "image_queries": [topic, "space", "mystery", "dark"]
        }
        
    full_script = [script_data["hook"]] + script_data["facts"]

    from audio import generate_audios
    audio_files = generate_audios(full_script)

    from fetch_background import get_background_images
    from CreateVideo import create_video
    
    bg_images = get_background_images(script_data["image_queries"], num_images=4)
    
    os.makedirs("output", exist_ok=True)
    s = re.sub(r"[^\w\s-]", "", topic).strip().lower()
    slug = re.sub(r"\s+", "_", s)[:60] or "video"
    out_path = os.path.join("output", f"{slug}.mp4")
    
    create_video(full_script, audio_files, bg_images, out_path, topic)
    print(f"  Video saved: {out_path}")

def main():
    topics = load_topics()
    s = load_state()
    today = date.today().isoformat()
    
    made_today = sum(1 for e in s["log"] if e["date"] == today)
    needed = PER_DAY - made_today
    
    print(f"\n=== YT Auto Generator ===")
    print(f"Need {needed} videos today.")
    
    if needed <= 0:
        print("Already made 5 videos today. Stopping.")
        return

    for i in range(needed):
        topic = next_topic(topics, s)
        if topic is None:
            print("QUEUE EMPTY")
            break
            
        print(f"\n--- Making Video {i+1}/{needed}: {topic} ---")
        try:
            generate_video(topic)
            s["done"].append(topic)
            s["log"].append({"topic": topic, "date": today})
            print(f"  Success: {topic}")
        except Exception as e:
            s["failed"][topic] = s["failed"].get(topic, 0) + 1
            print(f"  FAILED {topic}: {e}")
            
        save_state(s)

    remaining = len([t for t in topics if t not in s["done"]])
    if remaining < 10:
        print(f"::warning::Only {remaining} topics left in queue!")

if __name__ == "__main__":
    main()
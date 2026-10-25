import os
import re
import sys
import json
import random
import tempfile
from datetime import date
from pathlib import Path

STATE_FILE = Path("state.json")
BANK_FILE = Path("script_bank.json")
PER_DAY = 5  # Change to 5 for GitHub Actions
MAX_FAILS = 3

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"done": [], "failed": {}, "log": []}

def save_state(s):
    fd, tmp = tempfile.mkstemp(dir=".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)

def get_next_script(s):
    try:
        with open(BANK_FILE, "r") as f:
            bank = json.load(f)
    except Exception as e:
        print(f"  [Error] Could not load script_bank.json: {e}")
        return None

    done = set(s["done"])
    for script in bank:
        if script["topic"] not in done and s["failed"].get(script["topic"], 0) < MAX_FAILS:
            return script
            
    print("  [Script Bank] All scripts used! Resetting queue.")
    s["done"] = []
    return bank[0] if bank else None

def generate_video(script_data):
    topic = script_data["topic"]
    full_script = [script_data["hook"]] + script_data["facts"]

    print(f"  [Audio] Generating voiceovers...")
    from audio import generate_audios
    audio_files = generate_audios(full_script)

    print(f"  [Images] Fetching backgrounds...")
    from fetch_background import get_background_images
    queries = script_data.get("image_queries", [topic, f"{topic} close up", f"{topic} background", topic])
    bg_images = get_background_images(queries, num_images=4)
    
    print(f"  [Music] Fetching cinematic background track...")
    from fetch_music import get_background_music
    get_background_music()
    
    print(f"  [Video] Rendering...")
    from CreateVideo import create_video
    os.makedirs("output", exist_ok=True)
    s = re.sub(r"[^\w\s-]", "", topic).strip().lower()
    slug = re.sub(r"\s+", "_", s)[:60] or "video"
    out_path = os.path.join("output", f"{slug}.mp4")
    
    create_video(full_script, audio_files, bg_images, out_path, topic)
    print(f"  Video saved: {out_path}")

def main():
    s = load_state()
    today = date.today().isoformat()
    
    made_today = sum(1 for e in s["log"] if e["date"] == today)
    needed = PER_DAY - made_today
    
    print(f"\n=== YT Auto Generator ===")
    print(f"Need {needed} videos today.")
    
    if needed <= 0:
        print("Already made videos for today. Stopping.")
        return

    for i in range(needed):
        script_data = get_next_script(s)
        if not script_data:
            print("No scripts found. Please add scripts to script_bank.json.")
            break
            
        topic = script_data["topic"]
        print(f"\n--- Making Video {i+1}/{needed}: {topic} ---")
        
        try:
            generate_video(script_data)
            s["done"].append(topic)
            s["log"].append({"topic": topic, "date": today})
            print(f"  Success: {topic}")
        except Exception as e:
            s["failed"][topic] = s["failed"].get(topic, 0) + 1
            print(f"  FAILED {topic}: {e}")
            
        save_state(s)

if __name__ == "__main__":
    main()
import os
import re
import json
import tempfile
from datetime import date
from pathlib import Path

STATE_FILE = Path("state.json")
BANK_FILE = Path("script_bank.json")
PER_DAY = int(os.getenv("VIDEOS_PER_DAY", "5"))
MAX_FAILS = 3


def load_state():
    default = {"done": [], "failed": {}, "log": []}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            for key, value in default.items():
                state.setdefault(key, value)
            return state
        except json.JSONDecodeError:
            # Do not silently erase history: that could cause old scripts to repeat.
            raise RuntimeError("state.json is corrupted. Restore it from Git history before running.")
    return default


def save_state(state):
    fd, tmp = tempfile.mkstemp(dir=".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_bank():
    if not BANK_FILE.exists():
        return []
    return json.loads(BANK_FILE.read_text(encoding="utf-8"))


def get_next_script(state):
    bank = load_bank()
    done = set(state["done"])
    failed = state["failed"]
    for script in bank:
        topic = script.get("topic", "").strip()
        if topic and topic not in done and failed.get(topic, 0) < MAX_FAILS:
            return script
    return None


def generate_more_scripts(state):
    from generate_scripts import append_fresh_scripts

    bank = load_bank()
    # Include all bank topics, successful topics and exhausted failures so Gemini
    # cannot regenerate a script already seen by this channel.
    blocked = [s.get("topic", "") for s in bank]
    blocked.extend(state["done"])
    blocked.extend(topic for topic, attempts in state["failed"].items()
                   if attempts >= MAX_FAILS)
    return append_fresh_scripts(blocked)


def generate_video(script_data):
    topic = script_data["topic"]
    full_script = [script_data["hook"]] + script_data["facts"]

    print("  [Audio] Generating voiceovers...")
    from audio import generate_audios
    audio_files = generate_audios(full_script)

    print("  [Images] Fetching backgrounds...")
    from fetch_background import get_background_images
    queries = script_data.get(
        "image_queries",
        [topic, f"{topic} close up", f"{topic} background", topic],
    )
    bg_images = get_background_images(queries, num_images=4, topic=topic)

    print("  [Video] Rendering...")
    os.makedirs("output", exist_ok=True)
    slug_source = re.sub(r"[^\w\s-]", "", topic).strip().lower()
    slug = re.sub(r"\s+", "_", slug_source)[:60] or "video"
    out_path = os.path.join("output", f"{slug}.mp4")

    from CreateVideo import create_video
    create_video(full_script, audio_files, bg_images, out_path, topic)
    print(f"  Video saved: {out_path}")


def main():
    state = load_state()
    today = date.today().isoformat()
    is_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    if is_manual:
        print("  [Mode] Manual trigger detected.")
        needed = PER_DAY
    else:
        made_today = sum(1 for entry in state["log"] if entry.get("date") == today)
        needed = max(0, PER_DAY - made_today)

    print("\n=== YT Auto Generator ===")
    print(f"Need {needed} videos today.")
    if needed <= 0:
        print("Already made the daily quota. Stopping.")
        return

    for index in range(needed):
        script_data = get_next_script(state)
        if not script_data:
            print("  [Script Bank] No unused scripts. Asking Gemini for fresh scripts...")
            try:
                generate_more_scripts(state)
            except Exception as exc:
                print(f"  [Gemini] Could not replenish script bank: {exc}")
                break
            script_data = get_next_script(state)

        if not script_data:
            print("No unused scripts available. Stopping without recycling old topics.")
            break

        topic = script_data["topic"]
        print(f"\n--- Making Video {index + 1}/{needed}: {topic} ---")
        try:
            generate_video(script_data)
            if topic not in state["done"]:
                state["done"].append(topic)
            state["log"].append({"topic": topic, "date": today})
            print(f"  Success: {topic} (permanently consumed)")
        except Exception as exc:
            state["failed"][topic] = state["failed"].get(topic, 0) + 1
            print(f"  FAILED {topic}: {exc}")
            if state["failed"][topic] >= MAX_FAILS and topic not in state["done"]:
                state["done"].append(topic)
                print(f"  [Queue] Retired {topic} after {MAX_FAILS} failures; it will not be reused.")

        save_state(state)


if __name__ == "__main__":
    main()

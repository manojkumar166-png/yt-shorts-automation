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
    eligible = [s for s in bank if s.get("topic", "").strip() and s.get("topic", "").strip() not in done and failed.get(s.get("topic", "").strip(), 0) < MAX_FAILS]
    recent = {entry.get("category", "other") for entry in state["log"][-2:]}
    for script in eligible:
        if script.get("category", "other") not in recent:
            return script
    return eligible[0] if eligible else None


def generate_more_scripts(state, count):
    from generate_scripts import append_fresh_scripts

    bank = load_bank()
    # Include all bank topics, successful topics and exhausted failures so Gemini
    # cannot regenerate a script already seen by this channel.
    blocked = [s.get("topic", "") for s in bank]
    blocked.extend(state["done"])
    blocked.extend(topic for topic, attempts in state["failed"].items()
                   if attempts >= MAX_FAILS)
    return append_fresh_scripts(blocked, count=count)


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
        [topic, f"{topic} close up", f"{topic} background", f"{topic} detail", f"{topic} wide scene", f"{topic} atmosphere"],
    )
    # One vertical visual for each narrated section: hook plus five facts.
    bg_images = get_background_images(queries, num_images=len(full_script), topic=topic)

    print("  [Video] Rendering...")
    os.makedirs("output", exist_ok=True)
    slug_source = re.sub(r"[^\w\s-]", "", topic).strip().lower()
    slug = re.sub(r"\s+", "_", slug_source)[:60] or "video"
    out_path = os.path.join("output", f"{slug}.mp4")

    from CreateVideo import create_video
    create_video(full_script, audio_files, bg_images, out_path, topic)
    if not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f"Renderer did not create a valid video file: {out_path}")
    print(f"  Video saved: {out_path}")
    return out_path


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

    # Generate a completely fresh batch for this run; never fall back to older
    # queued scripts. This makes every day's planned videos new Gemini scripts.
    print(f"  [Gemini] Generating {needed} brand-new scripts for today's videos...")
    try:
        todays_scripts = generate_more_scripts(state, needed)
    except Exception as exc:
        print(f"  [Scripts] Daily script generation failed; stopping rather than reusing old scripts: {exc}")
        raise

    successful_videos = 0
    for index, script_data in enumerate(todays_scripts):
        topic = script_data["topic"]
        print(f"\n--- Making Video {index + 1}/{needed}: {topic} ---")
        try:
            video_path = generate_video(script_data)
            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
            telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
            if telegram_token and telegram_chat_id:
                from telegram_delivery import send_video
                send_video(video_path, telegram_token, telegram_chat_id, topic)
                print(f"  [Telegram] Delivered: {topic}")
            else:
                print("  [Telegram] Not configured; video remains available as a GitHub Actions artifact.")
            if topic not in state["done"]:
                state["done"].append(topic)
            state["log"].append({"topic": topic, "date": today, "category": script_data.get("category", "other"), "quality_score": script_data.get("quality_score", 0)})
            successful_videos += 1
            print(f"  Success: {topic} (permanently consumed)")
        except Exception as exc:
            state["failed"][topic] = state["failed"].get(topic, 0) + 1
            print(f"  FAILED {topic}: {exc}")
            if state["failed"][topic] >= MAX_FAILS and topic not in state["done"]:
                state["done"].append(topic)
                print(f"  [Queue] Retired {topic} after {MAX_FAILS} failures; it will not be reused.")

        save_state(state)

    if successful_videos != needed:
        raise RuntimeError(f"Video generation incomplete: created {successful_videos} of {needed} requested videos.")
    print(f"\\n[Complete] Successfully generated all {successful_videos} videos.")


if __name__ == "__main__":
    main()

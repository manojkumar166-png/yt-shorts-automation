import json
import os
from asset_fetcher import ensure_images

with open("script_bank.json", "r", encoding="utf-8") as f:
    scripts = json.load(f)

start_idx = 0
try:
    if os.path.exists("state.json"):
        with open("state.json", "r", encoding="utf-8") as state_file:
            state = json.load(state_file)
        start_idx = len(state.get("done", []))
except Exception as exc:
    print(f"Could not read generation state; starting from first script: {exc}")

# Prefetch remains stock-only so a scheduled run does not generate dozens
# of paid AI images for scripts that may not be selected.
for script in scripts[start_idx:start_idx + 14]:
    safe_id = "".join(
        c for c in script["topic"] if c.isalnum() or c in (" ", "_")
    ).rstrip().replace(" ", "_")
    print(f"Prefetching stock images for: {safe_id}")
    ensure_images(
        safe_id,
        script.get("image_queries", [script["topic"]] * 4),
        use_ai=False,
    )

import json, sys
from asset_fetcher import ensure_images

with open("script_bank.json", "r") as f:
    scripts = json.load(f)

start_idx = 0
try:
    import os
    if os.path.exists("state.json"):
        state = json.load(open("state.json"))
        start_idx = len(state.get("done", []))
except:
    pass

for s in scripts[start_idx:start_idx + 14]:
    safe_id = "".join(c for c in s["topic"] if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    print(f"Prefetching images for: {safe_id}")
    ensure_images(safe_id, s.get("image_queries", [s["topic"]] * 4))
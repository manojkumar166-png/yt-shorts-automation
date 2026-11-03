"""Generate fresh, one-time, research-backed YouTube Shorts scripts."""
import json, os, re, time
from pathlib import Path
from urllib.parse import urlparse
import requests

BANK_FILE = Path("script_bank.json")
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
BATCH_SIZE = int(os.getenv("GEMINI_SCRIPT_BATCH_SIZE", "10"))
MIN_SCORE = int(os.getenv("MIN_SCRIPT_QUALITY_SCORE", "70"))
CATEGORIES = {"science", "nature", "history", "technology", "mystery", "animals", "space", "other"}

def _extract_json(text):
    text = text.strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("Gemini response did not contain a JSON array")
    return json.loads(text[start:end + 1])

def _quality_score(item):
    words = len(item["hook"].split())
    facts, images, sources = item["facts"], item["image_queries"], item["sources"]
    score = 25 if 7 <= words <= 18 else 10 if 5 <= words <= 22 else 0
    score += 25 if all(8 <= len(x.split()) <= 32 for x in facts) else 10
    score += 20 if len({x.lower() for x in images}) == 4 and all(len(x.split()) >= 2 for x in images) else 5
    score += 20 if len(sources) >= 3 else 10 if len(sources) == 2 else 0
    score += 10 if not item["uncertain_claims"] else 0
    return score

def generate_scripts(existing_topics, count=BATCH_SIZE):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it in repository Actions secrets.")
    blocked = sorted({str(x).strip().lower() for x in existing_topics if str(x).strip()})
    prompt = f"""
Create exactly {count} original high-retention Shorts scripts.
For each: draft 3 distinct 8-16 word hook alternatives, select the strongest
into selected_hook, never start with Did you know; create a curiosity gap,
escalate across exactly 3 concise factual beats, and end with a payoff.
Assign one category: science, nature, history, technology, mystery, animals,
space, other. Research claims using Google Search. Provide 3-6 direct HTTPS
source URLs from reputable institutions, journals, museums, universities or
established science publications, preferring primary sources. List uncertain
claims in uncertain_claims; use [] only when sources firmly support every claim.
Include exactly 4 specific, visually distinct image prompts. Aim for 35-55 sec.
Avoid invented statistics, fake quotes and unsupported superlatives.
Do not repeat these topics: {json.dumps(blocked)}
Return ONLY JSON array. Each object keys: topic, category,
hook_alternatives (3 strings), selected_hook, facts (3 strings),
image_queries (4 strings), sources (3-6 URLs), uncertain_claims (array).
"""
    url = f"{API_BASE}/{DEFAULT_MODEL}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
               "tools": [{"google_search": {}}],
               "generationConfig": {"temperature": 0.7}}
    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            body = response.json()
            raw = body["candidates"][0]["content"]["parts"][0]["text"]
            items = _extract_json(raw)
            if not isinstance(items, list):
                raise ValueError("Gemini output is not a JSON array")
            accepted, seen = [], set(blocked)
            for item in items:
                if not isinstance(item, dict):
                    continue
                topic = re.sub(r"\s+", " ", str(item.get("topic", "")).strip())
                category = str(item.get("category", "other")).strip().lower()
                hooks, hook = item.get("hook_alternatives"), str(item.get("selected_hook", "")).strip()
                facts, images = item.get("facts"), item.get("image_queries")
                sources, uncertain = item.get("sources"), item.get("uncertain_claims")
                if (not topic or topic.lower() in seen or category not in CATEGORIES
                    or not isinstance(hooks, list) or len(hooks) != 3
                    or not all(isinstance(x, str) and x.strip() for x in hooks)
                    or hook not in hooks or not isinstance(facts, list) or len(facts) != 3
                    or not all(isinstance(x, str) and x.strip() for x in facts)
                    or not isinstance(images, list) or len(images) != 4
                    or not all(isinstance(x, str) and x.strip() for x in images)
                    or not isinstance(sources, list) or not 2 <= len(sources) <= 6
                    or not all(isinstance(x, str) and urlparse(x).scheme == "https" and urlparse(x).netloc for x in sources)
                    or not isinstance(uncertain, list)):
                    continue
                clean = {"topic": topic, "category": category,
                    "hook_alternatives": [x.strip() for x in hooks], "hook": hook,
                    "facts": [x.strip() for x in facts],
                    "image_queries": [x.strip() for x in images], "sources": sources,
                    "uncertain_claims": [str(x).strip() for x in uncertain if str(x).strip()]}
                clean["quality_score"] = _quality_score(clean)
                if clean["quality_score"] < MIN_SCORE:
                    print(f"  [Quality] Rejected {topic}: {clean['quality_score']} < {MIN_SCORE}")
                    continue
                accepted.append(clean)
                seen.add(topic.lower())
                if len(accepted) >= count:
                    break
            if not accepted:
                raise ValueError("No new scripts passed schema and quality checks")
            return accepted
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Gemini generation failed after 3 attempts: {last_error}")

def append_fresh_scripts(existing_topics):
    bank = json.loads(BANK_FILE.read_text(encoding="utf-8")) if BANK_FILE.exists() else []
    fresh = generate_scripts(existing_topics)
    known = {str(s.get("topic", "")).strip().lower() for s in bank}
    added = [s for s in fresh if s["topic"].lower() not in known]
    if not added:
        raise RuntimeError("No new topics generated; refusing to recycle scripts")
    bank.extend(added)
    temp = BANK_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(bank, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(BANK_FILE)
    print(f"  [Gemini] Added {len(added)} quality-screened scripts.")
    return added

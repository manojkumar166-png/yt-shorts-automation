"""Generate fresh, one-time, research-backed YouTube Shorts scripts."""
import json, os, re, time
from pathlib import Path
from urllib.parse import urlparse
import requests

BANK_FILE = Path("script_bank.json")
BANK_FILES = (Path("script_bank.json"), Path("scripts_bank.json"))
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
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
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    llm7_api_key = os.getenv("LLM7_API_KEY", "").strip()
    if not api_key and not groq_api_key and not llm7_api_key:
        print("  [LLM7] Anonymous access enabled; no API key required.")
    blocked = sorted({" ".join(str(x).split()).casefold() for x in existing_topics if str(x).strip()})
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
ABSOLUTE EXCLUSION LIST: Never generate, paraphrase, reword, or make a close variation of any topic in this list. These topics already exist in the repository script bank and are forbidden: {json.dumps(blocked)}
Return ONLY JSON array. Each object keys: topic, category,
hook_alternatives (3 strings), selected_hook, facts (3 strings),
image_queries (4 strings), sources (3-6 URLs), uncertain_claims (array).
"""
    # Gemini Flash-Lite first, then Flash, followed by Groq's free OpenAI-compatible API.
    models = [
        ("gemini", "gemini-3.5-flash-lite"),
        ("gemini", "gemini-3.1-flash-lite"),
        ("gemini", "gemini-3.8-flash"),
        ("gemini", "gemini-3.6-flash"),
    ]
    if groq_api_key:
        models.append(("groq", "openai/gpt-oss-120b"))
    # LLM7 supports anonymous turbo access; an optional token raises limits.
    models.append(("llm7", "gpt-oss:20b"))
    errors = []
    for provider, model in models:
        if provider == "gemini" and not api_key:
            continue
        if provider == "gemini":
            url = f"{API_BASE}/{model}:generateContent"
            headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                       "tools": [{"google_search": {}}],
                       "generationConfig": {"temperature": 0.7}}
            provider_label = "Gemini"
        else:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
            groq_prompt = prompt.replace("Research claims using Google Search.", "Do not claim to have browsed or verified sources live. Provide source URLs only when you are confident they are real; uncertain claims must be listed.")
            groq_prompt = groq_prompt.replace("Return ONLY JSON array.", "Return ONLY a valid JSON object with a single key scripts whose value is an array of script objects.")
            payload = {"model": model, "messages": [{"role": "user", "content": groq_prompt}],
                       "temperature": 0.7, "response_format": {"type": "json_object"}}
            provider_label = "Groq"
        elif provider == "llm7":
            url = "https://api.llm7.io/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            if llm7_api_key:
                headers["Authorization"] = f"Bearer {llm7_api_key}"
            llm7_prompt = prompt.replace("Research claims using Google Search.", "Do not claim to have browsed or verified sources live. Provide source URLs only when confident they are real; list uncertain claims.")
            llm7_prompt = llm7_prompt.replace("Return ONLY JSON array.", "Return ONLY a valid JSON object with a single key scripts whose value is an array of script objects.")
            payload = {"model": model, "messages": [{"role": "user", "content": llm7_prompt}],
                       "temperature": 0.7, "response_format": {"type": "json_object"}}
            if llm7_api_key:
                provider_label = "LLM7 (token)"
            else:
                provider_label = "LLM7 (anonymous)"
        print(f"  [{provider_label}] Trying model: {model}")
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code in (404, 429, 500, 502, 503, 504):
                    detail = response.text[:1200]
                    errors.append(f"{model}: HTTP {response.status_code}: {detail}")
                    # Short backoff for a transient 429/5xx, then move to the next model.
                    if attempt == 0 and response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After", "")
                        try:
                            delay = min(max(int(retry_after), 2), 20) if retry_after else 5
                        except ValueError:
                            delay = 5
                        print(f"  [{provider_label}] {model} returned {response.status_code}; retrying in {delay}s.")
                        time.sleep(delay)
                        continue
                    print(f"  [{provider_label}] Falling back after {model} returned HTTP {response.status_code}.")
                    break
                response.raise_for_status()
                body = response.json()
                raw = (body["candidates"][0]["content"]["parts"][0]["text"]
                       if provider == "gemini" else body["choices"][0]["message"]["content"])
                items = _extract_json(raw)
                if not isinstance(items, list):
                    raise ValueError("Gemini output is not a JSON array")
                accepted, seen = [], set(blocked)
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    topic = re.sub(r"\s+", " ", str(item.get("topic", "")).strip())
                    normalized_topic = " ".join(topic.split()).casefold()
                    category = str(item.get("category", "other")).strip().lower()
                    hooks, hook = item.get("hook_alternatives"), str(item.get("selected_hook", "")).strip()
                    facts, images = item.get("facts"), item.get("image_queries")
                    sources, uncertain = item.get("sources"), item.get("uncertain_claims")
                    if (not topic or normalized_topic in seen or category not in CATEGORIES
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
                    seen.add(normalized_topic)
                    if len(accepted) >= count:
                        break
                if len(accepted) != count:
                    raise ValueError(f"Only {len(accepted)} of {count} requested fresh scripts passed checks; refusing a partial batch")
                print(f"  [{provider_label}] Successfully generated scripts with {model}.")
                return accepted
            except requests.RequestException as exc:
                errors.append(f"{model}: {exc}")
                if attempt == 0:
                    time.sleep(3)
            except Exception as exc:
                # Invalid output/quality is not fixed by switching models repeatedly.
                errors.append(f"{model}: {exc}")
                break
    raise RuntimeError("All configured LLM providers failed. " + " | ".join(errors[-9:]))

def append_fresh_scripts(existing_topics, count=BATCH_SIZE):
    # Read both filename spellings if present; topics in either bank are forbidden.
    bank = []
    for bank_path in BANK_FILES:
        if bank_path.exists():
            contents = json.loads(bank_path.read_text(encoding="utf-8"))
            if not isinstance(contents, list):
                raise ValueError(f"{bank_path} must contain a JSON array")
            bank.extend(contents)

    known = {
        " ".join(str(item.get("topic", "")).split()).casefold()
        for item in bank if isinstance(item, dict) and item.get("topic")
    }
    blocked = {
        " ".join(str(topic).split()).casefold()
        for topic in existing_topics if str(topic).strip()
    }
    blocked.update(known)
    fresh = generate_scripts(blocked, count=count)
    added = [
        item for item in fresh
        if " ".join(item["topic"].split()).casefold() not in known
    ]
    if len(added) != count:
        raise RuntimeError(f"Expected {count} entirely new topics; got {len(added)}. Refusing to use bank topics.")
    bank.extend(added)
    temp = BANK_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(bank, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(BANK_FILE)
    print(f"  [Gemini] Added {len(added)} quality-screened scripts.")
    return added

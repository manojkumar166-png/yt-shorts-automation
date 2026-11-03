"""Generate fresh, one-time YouTube Shorts scripts with Gemini."""
import json
import os
import re
import time
from pathlib import Path

import requests

BANK_FILE = Path("script_bank.json")
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
BATCH_SIZE = int(os.getenv("GEMINI_SCRIPT_BATCH_SIZE", "10"))


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^\x60{3}(?:json)?\s*|\s*\x60{3}$", "", text, flags=re.I)
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("Gemini response did not contain a JSON array")
    return json.loads(text[start:end + 1])


def generate_scripts(existing_topics, count=BATCH_SIZE):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it under repository Settings > "
            "Secrets and variables > Actions."
        )

    blocked = sorted({str(x).strip().lower() for x in existing_topics if str(x).strip()})
    prompt = f"""
Create exactly {count} original, high-retention YouTube Shorts scripts for a
general science, nature, history, technology and surprising-facts channel.

Each script must:
- Open with a specific curiosity gap or surprising claim in a punchy hook
  (roughly 8-16 words); never start with "Did you know".
- Explain one clear subject in exactly 3 concise, factual narration beats.
- Be understandable without prior context and suitable for a 35-55 second Short.
- Use careful, defensible facts. Avoid invented statistics, fake quotes,
  conspiracy claims, medical advice, and unsupported superlatives.
- End the third fact with a satisfying reveal or thought-provoking payoff.
- Have four short, visually distinct image_queries suitable for AI image generation.
- Be genuinely different from the topics already used or in the current bank.

Do not repeat or closely paraphrase these existing topics:
{json.dumps(blocked, ensure_ascii=False)}

Return ONLY a valid JSON array. Each object must have exactly these keys:
"topic" (short unique lowercase title), "hook" (one spoken hook sentence),
"facts" (array of exactly 3 spoken sentences), "image_queries" (array of exactly 4 strings).
No markdown, no commentary, no extra keys.
"""

    url = f"{API_BASE}/{DEFAULT_MODEL}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "responseMimeType": "application/json",
        },
    }

    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            generated = _extract_json(text)
            if not isinstance(generated, list):
                raise ValueError("Gemini output is not a JSON array")

            accepted = []
            seen = set(blocked)
            for item in generated:
                if not isinstance(item, dict):
                    continue
                topic = re.sub(r"\s+", " ", str(item.get("topic", "")).strip())
                hook = str(item.get("hook", "")).strip()
                facts = item.get("facts")
                images = item.get("image_queries")
                key = topic.lower()
                if (not topic or key in seen or not hook or
                    not isinstance(facts, list) or len(facts) != 3 or
                    not all(isinstance(x, str) and x.strip() for x in facts) or
                    not isinstance(images, list) or len(images) != 4 or
                    not all(isinstance(x, str) and x.strip() for x in images)):
                    continue
                accepted.append({
                    "topic": topic,
                    "hook": hook,
                    "facts": [x.strip() for x in facts],
                    "image_queries": [x.strip() for x in images],
                })
                seen.add(key)
                if len(accepted) >= count:
                    break

            if not accepted:
                raise ValueError("Gemini returned no valid, unused scripts")
            return accepted
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Gemini script generation failed after 3 attempts: {last_error}")


def append_fresh_scripts(existing_topics):
    bank = []
    if BANK_FILE.exists():
        bank = json.loads(BANK_FILE.read_text(encoding="utf-8"))
    new_scripts = generate_scripts(existing_topics)
    known = {str(s.get("topic", "")).strip().lower() for s in bank}
    added = [s for s in new_scripts if s["topic"].lower() not in known]
    if not added:
        raise RuntimeError("Gemini did not produce any new topics; refusing to recycle scripts")
    bank.extend(added)
    temp = BANK_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(bank, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(BANK_FILE)
    print(f"  [Gemini] Added {len(added)} fresh scripts to script_bank.json.")
    return added


import os
import time

# --- YOU CAN ALSO PASTE KEY HERE DIRECTLY (optional) ---
# If you don't want to use set GROQ_API_KEY each time, paste full key here:
HARDCODED_GROQ_KEY = ""  # e.g. "gsk_abc123..."

def _parse_facts(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    facts = []
    for line in lines:
        cleaned = line.lstrip('123.-) ').strip()
        if len(cleaned) > 10:
            if cleaned.lower().startswith('fact'):
                cleaned = cleaned.split(':',1)[-1].strip() if ':' in cleaned else cleaned
            facts.append(cleaned)
    return facts[:3]

def _get_key():
    # Use env first, then hardcoded
    key = os.getenv("GROQ_API_KEY") or HARDCODED_GROQ_KEY
    if not key or "YOUR" in key or len(key) < 20:
        raise ValueError("GROQ_API_KEY not set! Set with: set GROQ_API_KEY=gsk_... (full 100-char key)")
    return key

def _try_groq(topic):
    print("-> Trying Groq...")
    from groq import Groq
    client = Groq(api_key=_get_key())
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": f"You are a YouTube Shorts writer. Topic: {topic}. Give exactly 3 curious short facts, 1 sentence each, max 20 words. Return as numbered list."}],
        temperature=0.8, max_tokens=300)
    return completion.choices[0].message.content

def generate_facts(topic: str):
    try:
        text = _try_groq(topic)
        facts = _parse_facts(text)
        if len(facts) >= 1:
            print(f"OK Generated: {facts}")
            return facts
    except Exception as e:
        print(f"Failed: {e}")
        raise RuntimeError(f"Groq failed: {e}. Check your API key is FULL key (not cut) and valid at https://console.groq.com/keys")

if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "black holes"
    print(generate_facts(topic))

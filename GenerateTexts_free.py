import os

def generate_facts(topic: str):
    api = os.getenv("GEMINI_API_KEY")
    if not api or len(api) < 20:
        raise ValueError("GEMINI_API_KEY not set! Go to https://aistudio.google.com/app/apikey -> Create key -> Copy FULL key (AIzaSy...) -> set GEMINI_API_KEY=AIza...")

    import google.generativeai as genai
    genai.configure(api_key=api)
    
    print("-> Trying gemini-1.5-flash...")
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"You are a viral YouTube Shorts writer. Topic: {topic}. Give exactly 3 shocking facts. Each 1 sentence, max 20 words. Numbered list."
    response = model.generate_content(prompt)
    text = response.text
    
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    facts = []
    for line in lines:
        cleaned = line.lstrip("123.-) ").strip()
        if len(cleaned) > 10:
            if cleaned.lower().startswith("fact"):
                cleaned = cleaned.split(":",1)[-1].strip() if ":" in cleaned else cleaned
            facts.append(cleaned)
    facts = facts[:3]
    print(f"OK Generated: {facts}")
    return facts
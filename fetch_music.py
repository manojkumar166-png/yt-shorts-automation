import os
import random
import requests
from dotenv import load_dotenv

load_dotenv()
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY", "").strip()

def _download_pixabay_audio(query, filename):
    if not PIXABAY_KEY: 
        return False
    url = "https://pixabay.com/api/"
    params = {
        "key": PIXABAY_KEY,
        "q": query,
        "media_type": "music",
        "per_page": 5,
        "safesearch": "true"
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        
        if not hits:
            print(f"  [Audio] No results found for '{query}'")
            return False
            
        track = random.choice(hits)
        audio_url = track.get("audio")
        if not audio_url: 
            return False
            
        res = requests.get(audio_url, timeout=30)
        res.raise_for_status()
        with open(filename, "wb") as f:
            f.write(res.content)
        return True
    except Exception as e:
        print(f"  [Audio] Failed to download {filename}: {e}")
        return False

def get_background_music():
    print("  [Music] Fetching cinematic background music...")
    query = random.choice(["cinematic", "suspense", "dark ambient", "epic"])
    if _download_pixabay_audio(query, "bg_music.mp3"):
        print("  [Music] Successfully downloaded bg_music.mp3")
        
    print("  [SFX] Fetching whoosh sound effect...")
    if _download_pixabay_audio("whoosh", "whoosh.mp3"):
        print("  [SFX] Successfully downloaded whoosh.mp3")
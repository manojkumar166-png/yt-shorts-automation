import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY", "").strip()

def get_background_images(queries, num_images=4):
    print(f"  [Background] Fetching {num_images} HD images automatically...")
    
    if not PIXABAY_KEY:
        print("  [Background] Error: PIXABAY_API_KEY missing in .env")
        return []

    if os.path.exists("background"):
        for f in os.listdir("background"):
            if f.startswith("bg_"):
                try: os.remove(os.path.join("background", f))
                except: pass
    else:
        os.makedirs("background")

    image_paths = []
    
    # Ensure we have 4 queries, fill with generic if needed
    while len(queries) < num_images:
        queries.append("space galaxy")
        
    for i in range(num_images):
        query = queries[i].replace("_", " ").replace("*", "").strip()
        print(f"  [Background] Searching Pixabay for: {query}")
        filename = f"background/bg_{i}.jpg"
        success = False
        
        url = "https://pixabay.com/api/"
        params = {
            "key": PIXABAY_KEY,
            "q": query,
            "image_type": "photo",
            "orientation": "vertical",
            "per_page": 5,
            "safesearch": "true"
        }
        
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            hits = r.json().get("hits", [])
            
            for hit in hits:
                img_url = hit.get("largeImageURL")
                if not img_url: continue
                
                try:
                    res = requests.get(img_url, timeout=20)
                    res.raise_for_status()
                    
                    img = Image.open(BytesIO(res.content)).convert('RGB')
                    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
                    img.save(filename, "JPEG", quality=100)
                    
                    image_paths.append(filename)
                    print(f"  [Background] Image {i+1} downloaded successfully.")
                    success = True
                    break
                except Exception:
                    continue
        except Exception as e:
            print(f"  [Background] Failed: {e}")
            
        if not success:
            print(f"  [Background] Image {i+1} failed. Using gradient.")
            img = Image.new('RGB', (1080, 1920), color=(10, 12, 30))
            img.save(filename, "JPEG")
            image_paths.append(filename)
            
    return image_paths
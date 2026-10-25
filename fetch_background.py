import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY", "").strip()

def get_background_images(queries, num_images=4):
    print(f"  [Background] Fetching {num_images} HD images...")
    if not PIXABAY_KEY: return []

    if os.path.exists("background"):
        for f in os.listdir("background"):
            if f.startswith("bg_"):
                try: os.remove(os.path.join("background", f))
                except: pass
    else:
        os.makedirs("background")

    image_paths = []
    downloaded_urls = set()
    
    while len(queries) < num_images:
        queries.append("abstract")
        
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
            "per_page": 15, 
            "safesearch": "true"
        }
        
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            hits = r.json().get("hits", [])
            
            for hit in hits:
                img_url = hit.get("largeImageURL")
                if not img_url or img_url in downloaded_urls: continue
                
                try:
                    res = requests.get(img_url, timeout=20)
                    res.raise_for_status()
                    img = Image.open(BytesIO(res.content)).convert('RGB')
                    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
                    img.save(filename, "JPEG", quality=100)
                    image_paths.append(filename)
                    downloaded_urls.add(img_url)
                    print(f"  [Background] Image {i+1} downloaded.")
                    success = True
                    break
                except: continue
        except Exception as e:
            print(f"  [Background] Failed: {e}")
            
        if not success:
            print(f"  [Background] Image {i+1} failed. Using cinematic gradient.")
            img = Image.new('RGB', (1080, 1920), color=(10, 12, 30))
            for y in range(1920):
                r_val = 10 + int((y / 1920) * 20)
                g_val = 12 + int((y / 1920) * 15)
                b_val = 30 + int((y / 1920) * 10)
                for x in range(1080):
                    img.putpixel((x, y), (r_val, g_val, b_val))
            img.save(filename, "JPEG")
            image_paths.append(filename)
            
    return image_paths
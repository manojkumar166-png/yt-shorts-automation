import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import random

load_dotenv()
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY", "").strip()

def get_background_images(queries, num_images=4):
    print(f"  [Background] Fetching {num_images} HD images...")
    
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
        filename = f"background/bg_{i}.jpg"
        success = False
        
        # --- METHOD 1: Try Pixabay ---
        if PIXABAY_KEY:
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
                r = requests.get(url, params=params, timeout=10)
                if r.status_code == 200:
                    hits = r.json().get("hits", [])
                    for hit in hits:
                        img_url = hit.get("largeImageURL")
                        if not img_url or img_url in downloaded_urls: continue
                        
                        res = requests.get(img_url, timeout=15)
                        if res.status_code == 200:
                            img = Image.open(BytesIO(res.content)).convert('RGB')
                            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
                            img.save(filename, "JPEG", quality=100)
                            image_paths.append(filename)
                            downloaded_urls.add(img_url)
                            print(f"  [Background] Image {i+1} downloaded (Pixabay).")
                            success = True
                            break
            except Exception as e:
                pass

        # --- METHOD 2: Try Lorem Picsum (If Pixabay fails) ---
        if not success:
            try:
                picsum_url = f"https://picsum.photos/1080/1920?random={i}"
                res = requests.get(picsum_url, timeout=15)
                res.raise_for_status()
                img = Image.open(BytesIO(res.content)).convert('RGB')
                img.save(filename, "JPEG", quality=100)
                image_paths.append(filename)
                print(f"  [Background] Image {i+1} downloaded (Picsum Fallback).")
                success = True
            except Exception:
                pass
                
        # --- METHOD 3: Gradient Fallback ---
        if not success:
            print(f"  [Background] Image {i+1} failed. Using gradient.")
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
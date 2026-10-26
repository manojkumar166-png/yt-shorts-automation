import os
import requests
import json
from PIL import Image
from io import BytesIO
from pathlib import Path

ASSETS = Path("assets")

def ensure_images(script_id, queries):
    """Downloads images using your exact Wikipedia/Pixabay logic and caches them."""
    d = ASSETS / script_id
    d.mkdir(parents=True, exist_ok=True)
    
    image_paths = []
    downloaded_urls = set()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    while len(queries) < 4:
        queries.append("abstract background")
        
    for i in range(4):
        filename = d / f"bg_{i}.jpg"
        
        # If image is already cached, skip downloading!
        if filename.exists():
            image_paths.append(str(filename))
            continue
            
        query = queries[i].replace("_", " ").replace("*", "").strip()
        print(f"  [Background] Searching for: {query}")
        success = False
        
        # Method 1: Wikipedia
        try:
            safe_query = query.replace(" ", "_")
            url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{safe_query}"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                items = r.json().get("items", [])
                for item in items:
                    if item.get("type") == "image" and item.get("srcset"):
                        img_url = item["srcset"][0]["src"]
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                            
                        if img_url in downloaded_urls: continue
                        
                        res = requests.get(img_url, headers=headers, timeout=20)
                        res.raise_for_status()
                        
                        img = Image.open(BytesIO(res.content)).convert('RGB')
                        img.save(filename, "JPEG", quality=100) # KEEPS ORIGINAL ASPECT RATIO
                        
                        image_paths.append(str(filename))
                        downloaded_urls.add(img_url)
                        print(f"  [Background] Image {i+1} downloaded (Wikipedia).")
                        success = True
                        break
        except Exception as e:
            print(f"  [Background] Wikipedia failed: {e}")

        # Method 2: Pixabay
        if not success:
            pixabay_key = os.getenv("PIXABAY_API_KEY", "").strip()
            if pixabay_key:
                try:
                    url = "https://pixabay.com/api/"
                    params = {"key": pixabay_key, "q": query, "image_type": "photo", "orientation": "vertical", "per_page": 5, "safesearch": "true"}
                    r = requests.get(url, params=params, timeout=15)
                    hits = r.json().get("hits", [])
                    for hit in hits:
                        img_url = hit.get("largeImageURL")
                        if not img_url or img_url in downloaded_urls: continue
                        
                        res = requests.get(img_url, timeout=20)
                        res.raise_for_status()
                        img = Image.open(BytesIO(res.content)).convert('RGB')
                        img.save(filename, "JPEG", quality=100) # KEEPS ORIGINAL ASPECT RATIO
                        
                        image_paths.append(str(filename))
                        downloaded_urls.add(img_url)
                        print(f"  [Background] Image {i+1} downloaded (Pixabay).")
                        success = True
                        break
                except:
                    pass

        # Method 3: Gradient Fallback
        if not success:
            print(f"  [Background] Image {i+1} failed. Using gradient.")
            img = Image.new('RGB', (1080, 1920), color=(10, 12, 30))
            img.save(filename, "JPEG")
            image_paths.append(str(filename))
            
    return image_paths
import os
import requests
from PIL import Image
from io import BytesIO

def get_background_images(queries, num_images=4):
    print(f"  [Background] Fetching {num_images} images...")
    
    if os.path.exists("background"):
        for f in os.listdir("background"):
            if f.startswith("bg_"):
                try: os.remove(os.path.join("background", f))
                except: pass
    else:
        os.makedirs("background")

    image_paths = []
    headers = {"User-Agent": "VideoGeneratorBot/1.0"}

    for i, query in enumerate(queries[:num_images]):
        url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": "6",
            "gsrlimit": "5", "prop": "imageinfo", "iiprop": "url|size|mime"
        }
        
        try:
            r = requests.get(url, params=params, headers=headers, timeout=15)
            pages = r.json().get("query", {}).get("pages", {})
            sorted_pages = sorted(pages.values(), key=lambda x: x.get("index", 0))
            
            for page in sorted_pages:
                info = page.get("imageinfo", [{}])[0]
                if info.get("mime") == "image/svg+xml": continue
                img_url = info.get("url")
                width = info.get("width", 0)
                
                if width >= 1080:
                    filename = f"background/bg_{i}.jpg"
                    img_data = requests.get(img_url, headers=headers, timeout=20).content
                    img = Image.open(BytesIO(img_data)).convert('RGB')
                    img.save(filename, "JPEG", quality=100)
                    image_paths.append(filename)
                    print(f"  [Background] Image {i+1} downloaded ({width}px).")
                    break
        except Exception as e:
            print(f"  [Background] Failed for query '{query}': {e}")
            
    return image_paths
import os
import requests
import time
from PIL import Image
from io import BytesIO

def get_background_images(topic, num_images=3):
    print(f"  [Background] Fetching 3 TRUE 4K images for: {topic}...")
    
    if os.path.exists("background"):
        for f in os.listdir("background"):
            if f.startswith("bg_"):
                try:
                    os.remove(os.path.join("background", f))
                except:
                    pass
    else:
        os.makedirs("background")

    image_paths = []
    url = "https://commons.wikimedia.org/w/api.php"
    
    # We ask for the ORIGINAL file (4K/8K), not the thumbnail
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {topic}",
        "gsrnamespace": "6",
        "gsrlimit": "30", # Fetch more options to find the biggest ones
        "prop": "imageinfo",
        "iiprop": "url|size|mime"
    }

    headers = {"User-Agent": "VideoGeneratorBot/1.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        pages = data.get("query", {}).get("pages", {})
        sorted_pages = sorted(pages.values(), key=lambda x: x.get("index", 0))
        
        for page in sorted_pages:
            if len(image_paths) >= num_images:
                break
                
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                continue
                
            info = imageinfo[0]
            
            # Skip if it's an SVG or not a standard image
            if info.get("mime") == "image/svg+xml":
                continue
                
            # Get the original 4K URL
            img_url = info.get("url")
            width = info.get("width", 0)
            
            # Ensure it's actually high quality (at least 1080 width)
            if width < 1080:
                continue

            filename = f"background/bg_{len(image_paths)}.jpg"
            
            try:
                img_data = requests.get(img_url, headers=headers, timeout=30).content
                img = Image.open(BytesIO(img_data))
                
                # Convert to high-quality RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(filename, "JPEG", quality=100)
                
                image_paths.append(filename)
                print(f"  [Background] Downloaded 4K Image {len(image_paths)}/{num_images} (Res: {width}px)")
            except Exception as e:
                pass
                
        return image_paths

    except Exception as e:
        print(f"  [Background] Failed to fetch images: {e}")
        return []
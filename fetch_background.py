import os
import shutil
from asset_fetcher import ensure_images

def get_background_images(queries, num_images=4, topic=""):
    print(f"  [Background] Checking cache for {num_images} HD images...")
    
    if os.path.exists("background"):
        for f in os.listdir("background"):
            if f.startswith("bg_"):
                try: os.remove(os.path.join("background", f))
                except: pass
    else:
        os.makedirs("background")

    image_paths = []
    
    safe_id = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    
    # 1. Try to load from cache
    if os.path.exists(f"assets/{safe_id}"):
        for i in range(4):
            src = f"assets/{safe_id}/bg_{i}.jpg"
            if os.path.exists(src):
                dest = f"background/bg_{i}.jpg"
                shutil.copy(src, dest)
                image_paths.append(dest)
                
    # 2. If cache is missing, download them
    if len(image_paths) < num_images:
        print(f"  [Background] Cache miss. Downloading...")
        cached_paths = ensure_images(safe_id, queries)
        for i, path in enumerate(cached_paths[:num_images]):
            dest = f"background/bg_{i}.jpg"
            shutil.copy(path, dest)
            image_paths.append(dest)
            
    return image_paths
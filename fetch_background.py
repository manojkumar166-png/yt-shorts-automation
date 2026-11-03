import os
import shutil
from asset_fetcher import ensure_images


def get_background_images(queries, num_images=12, topic=""):
    print(f"  [Background] Checking cache for {num_images} portrait images...")

    if os.path.exists("background"):
        for name in os.listdir("background"):
            if name.startswith("bg_"):
                try:
                    os.remove(os.path.join("background", name))
                except OSError:
                    pass
    else:
        os.makedirs("background")

    safe_id = "".join(c for c in topic if c.isalnum() or c in (" ", "_")).rstrip().replace(" ", "_")
    asset_dir = os.path.join("assets", safe_id)
    cached_paths = [
        os.path.join(asset_dir, f"bg_{i}.jpg")
        for i in range(num_images)
    ]

    # Reuse only a complete cache. A partial four-image cache must not be
    # duplicated to fill a six-scene video.
    if all(os.path.isfile(path) for path in cached_paths):
        print("  [Background] Complete image cache found.")
    else:
        print("  [Background] Cache miss or incomplete cache. Generating missing images...")
        cached_paths = ensure_images(safe_id, queries, num_images=num_images)[:num_images]

    image_paths = []
    for i, path in enumerate(cached_paths):
        dest = os.path.join("background", f"bg_{i}.jpg")
        shutil.copy(path, dest)
        image_paths.append(dest)

    if len(image_paths) != num_images:
        raise RuntimeError(f"Expected {num_images} background images, got {len(image_paths)}")
    return image_paths

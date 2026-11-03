import os
import requests
from PIL import Image
from io import BytesIO
from pathlib import Path

ASSETS = Path("assets")


def _make_ai_prompt(topic, query, index):
    subject = (query or topic).replace("_", " ").strip()
    return (
        f"Create a premium cinematic visual for a vertical YouTube Short about {topic}. "
        f"Main subject: {subject}. Scene variation {index + 1}. "
        "High-detail professional photography, dramatic but natural lighting, "
        "strong composition, realistic textures, visually clear focal subject, "
        "rich depth, no text, no captions, no watermark. Compose for a 9:16 "
        "portrait video; keep the main subject near the center so it survives cropping."
    )


def ensure_images(script_id, queries, use_ai=True):
    """Create/cache four images. OVHcloud is optional; stock sources remain fallback."""
    d = ASSETS / script_id
    d.mkdir(parents=True, exist_ok=True)
    image_paths = []
    downloaded_urls = set()

    queries = list(queries or [])
    while len(queries) < 4:
        queries.append("abstract background")

    use_ovh = use_ai and bool(os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN", "").strip())
    if use_ovh:
        from ovhcloud_image import generate_image

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ShortsImageFetcher/1.0)"
    }

    for i in range(4):
        filename = d / f"bg_{i}.jpg"
        source_marker = d / f"bg_{i}.source"
        cached_source = source_marker.read_text(encoding="utf-8").strip() if source_marker.exists() else "stock"
        if filename.exists():
            try:
                with Image.open(filename) as cached:
                    cached.verify()
                # If OVHcloud is enabled, replace a stock-prefetched image once.
                # Keep already-generated OVHcloud images on subsequent runs.
                if not (use_ovh and cached_source != "ovhcloud"):
                    image_paths.append(str(filename))
                    continue
            except Exception:
                filename.unlink(missing_ok=True)

        query = str(queries[i]).replace("_", " ").replace("*", "").strip()
        success = False

        # 1. OVHcloud SDXL (opt-in via secret; generated only for the active video).
        if use_ovh:
            try:
                prompt = _make_ai_prompt(script_id.replace("_", " "), query, i)
                generate_image(prompt, str(filename))
                source_marker.write_text("ovhcloud", encoding="utf-8")
                image_paths.append(str(filename))
                print(f"  [Background] Image {i + 1} generated (OVHcloud SDXL).")
                success = True
            except Exception as exc:
                print(f"  [Background] OVHcloud failed for image {i + 1}: {exc}")

        # 2. Wikipedia media search.
        if not success:
            try:
                safe_query = query.replace(" ", "_")
                url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{safe_query}"
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    for item in response.json().get("items", []):
                        if item.get("type") != "image" or not item.get("srcset"):
                            continue
                        img_url = item["srcset"][0]["src"]
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                        if img_url in downloaded_urls:
                            continue
                        image_response = requests.get(img_url, headers=headers, timeout=25)
                        image_response.raise_for_status()
                        image = Image.open(BytesIO(image_response.content)).convert("RGB")
                        image.save(filename, "JPEG", quality=94, optimize=True)
                        downloaded_urls.add(img_url)
                        source_marker.write_text("stock", encoding="utf-8")
                        image_paths.append(str(filename))
                        print(f"  [Background] Image {i + 1} downloaded (Wikipedia).")
                        success = True
                        break
            except Exception as exc:
                print(f"  [Background] Wikipedia failed: {exc}")

        # 3. Pixabay.
        if not success:
            pixabay_key = os.getenv("PIXABAY_API_KEY", "").strip()
            if pixabay_key:
                try:
                    response = requests.get(
                        "https://pixabay.com/api/",
                        params={
                            "key": pixabay_key,
                            "q": query,
                            "image_type": "photo",
                            "orientation": "vertical",
                            "per_page": 8,
                            "safesearch": "true",
                        },
                        timeout=20,
                    )
                    response.raise_for_status()
                    for hit in response.json().get("hits", []):
                        img_url = hit.get("largeImageURL")
                        if not img_url or img_url in downloaded_urls:
                            continue
                        image_response = requests.get(img_url, timeout=25)
                        image_response.raise_for_status()
                        image = Image.open(BytesIO(image_response.content)).convert("RGB")
                        image.save(filename, "JPEG", quality=94, optimize=True)
                        downloaded_urls.add(img_url)
                        source_marker.write_text("stock", encoding="utf-8")
                        image_paths.append(str(filename))
                        print(f"  [Background] Image {i + 1} downloaded (Pixabay).")
                        success = True
                        break
                except Exception as exc:
                    print(f"  [Background] Pixabay failed: {exc}")

        # 4. Safe visual fallback.
        if not success:
            print(f"  [Background] Image {i + 1} unavailable. Using gradient fallback.")
            Image.new("RGB", (1080, 1920), color=(10, 12, 30)).save(filename, "JPEG")
            source_marker.write_text("fallback", encoding="utf-8")
            image_paths.append(str(filename))

    return image_paths

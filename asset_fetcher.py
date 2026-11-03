import os
from pathlib import Path

from PIL import Image

ASSETS = Path("assets")


def _make_ai_prompt(topic, query, index):
    subject = (query or topic).replace("_", " ").strip()
    return (
        f"Create a premium cinematic visual for a vertical YouTube Short about {topic}. "
        f"Main subject: {subject}. Scene variation {index + 1}. "
        "High-detail professional photography, dramatic but natural lighting, "
        "strong composition, realistic textures, visually clear focal subject, "
        "rich depth, no text, no captions, no watermark. Compose for a 9:16 "
        "portrait video; keep the main subject near the center."
    )


def ensure_images(script_id, queries, use_ai=True, num_images=6):
    """Create/cache one 9:16 AI visual per narration section."""
    d = ASSETS / script_id
    d.mkdir(parents=True, exist_ok=True)
    image_paths = []

    queries = list(queries or [])
    while len(queries) < num_images:
        queries.append("cinematic abstract atmosphere")

    use_ovh = bool(use_ai)

    from ai_horde_image import generate_image as generate_horde
    if use_ovh:
        from ovhcloud_image import generate_image as generate_ovh

    for i in range(num_images):
        filename = d / f"bg_{i}.jpg"
        source_marker = d / f"bg_{i}.source"
        cached_source = (
            source_marker.read_text(encoding="utf-8").strip()
            if source_marker.exists() else "legacy"
        )

        if filename.exists():
            try:
                with Image.open(filename) as cached:
                    cached.verify()
                # Prefer OVHcloud-generated images. Reuse either valid AI
                # provider's cache when OVH is not requested; replace old
                # stock/legacy caches.
                if not (use_ovh and cached_source != "ovhcloud") and cached_source in {
                    "ovhcloud", "ai_horde"
                }:
                    image_paths.append(str(filename))
                    continue
            except Exception:
                filename.unlink(missing_ok=True)

        query = str(queries[i]).replace("_", " ").replace("*", "").strip()
        prompt = _make_ai_prompt(script_id.replace("_", " "), query, i)
        generated = False

        if use_ovh:
            try:
                generate_ovh(prompt, str(filename))
                source_marker.write_text("ovhcloud", encoding="utf-8")
                print(f"  [Background] Image {i + 1} generated (anonymous OVHcloud SDXL).")
                generated = True
            except Exception as exc:
                print(f"  [Background] Anonymous OVHcloud failed for image {i + 1}: {exc}")

        if not generated:
            try:
                generate_horde(prompt, str(filename))
                source_marker.write_text("ai_horde", encoding="utf-8")
                print(f"  [Background] Image {i + 1} generated (anonymous AI Horde).")
                generated = True
            except Exception as exc:
                print(f"  [Background] AI Horde failed for image {i + 1}: {exc}")

        if not generated:
            # Keep the render pipeline alive if both remote generators fail.
            print(f"  [Background] Image {i + 1} unavailable. Using gradient fallback.")
            Image.new("RGB", (1080, 1920), color=(10, 12, 30)).save(filename, "JPEG")
            source_marker.write_text("fallback", encoding="utf-8")

        image_paths.append(str(filename))

    return image_paths

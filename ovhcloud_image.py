"""Anonymous OVHcloud SDXL image generation.

Uses OVHcloud's public Stable Diffusion XL endpoint. No API key,
access token, account secret, or authorization header is required.
The public endpoint is rate-limited; requests are spaced at 31 seconds.
"""
import base64
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

API_URL = "https://stable-diffusion-xl.endpoints.kepler.ai.cloud.ovh.net/api/text2image"
TIMEOUT = (20, 180)
_LAST_CALL = 0.0


def generate_image(prompt: str, output_path: str) -> str:
    global _LAST_CALL

    # Public anonymous endpoint: respect its limit of two requests/minute.
    wait = max(0.0, 31.0 - (time.monotonic() - _LAST_CALL))
    if wait:
        time.sleep(wait)
    _LAST_CALL = time.monotonic()

    response = requests.post(
        API_URL,
        headers={
            "accept": "application/octet-stream",
            "Content-Type": "application/json",
        },
        json={
            "prompt": prompt,
            "negative_prompt": (
                "text, letters, typography, watermark, logo, signature, border, "
                "collage, split screen, duplicate subjects, extra limbs, malformed "
                "hands, deformed face, distorted anatomy, blurry, pixelated, low "
                "detail, flat lighting, oversaturated, noisy, jpeg artifacts"
            ),
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        encoded = (response.json().get("data") or [{}])[0].get("b64_json")
        if not encoded:
            raise ValueError("OVHcloud returned no image data")
        image_bytes = base64.b64decode(encoded)
    else:
        image_bytes = response.content

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "JPEG", quality=94, optimize=True)
    return output_path

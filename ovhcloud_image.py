"""OVHcloud AI Endpoints image generation (SDXL).

Enable by setting OVH_AI_ENDPOINTS_ACCESS_TOKEN. If the key is absent or
the provider fails, the caller can continue with stock-image fallbacks.
"""
import base64
import os
import time
from pathlib import Path

import requests
from PIL import Image
from io import BytesIO

API_URL = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/images/generations"
MODEL = "stable-diffusion-xl-base-v10"
TIMEOUT = (20, 180)


def generate_image(prompt: str, output_path: str) -> str:
    token = os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("OVH_AI_ENDPOINTS_ACCESS_TOKEN is not configured")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1,
    }

    last_error = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                API_URL, headers=headers, json=payload, timeout=TIMEOUT
            )
            response.raise_for_status()
            data = response.json()["data"][0]
            image_bytes = base64.b64decode(data["b64_json"], validate=True)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, "JPEG", quality=94, optimize=True)
            return output_path
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"OVHcloud image generation failed after 3 attempts: {last_error}")

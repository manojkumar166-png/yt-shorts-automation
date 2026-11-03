"""Anonymous AI Horde image generation client.

Uses the public anonymous API identity (0000000000); no account or API key
is required. Anonymous requests have the lowest queue priority.
"""
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

API = "https://aihorde.net/api/v2"
ANONYMOUS_KEY = "0000000000"
HEADERS = {
    "apikey": ANONYMOUS_KEY,
    "Client-Agent": "yt-shorts-automation:1.0.0:github.com/manojkumar166-png/yt-shorts-automation",
}
CONNECT_TIMEOUT = 20
POLL_INTERVAL = 5
MAX_WAIT_SECONDS = 900


def generate_image(prompt: str, output_path: str) -> str:
    payload = {
        "prompt": prompt,
        "params": {
            "n": 1,
            "width": 512,
            "height": 768,
            "steps": 25,
            "cfg_scale": 7.5,
            "sampler_name": "k_euler_a",
        },
        "nsfw": False,
        "censor_nsfw": True,
        "trusted_workers": False,
        "dry_run": False,
    }

    response = requests.post(
        f"{API}/generate/async",
        headers=HEADERS,
        json=payload,
        timeout=(CONNECT_TIMEOUT, 60),
    )
    response.raise_for_status()
    request_id = response.json().get("id")
    if not request_id:
        raise RuntimeError(f"AI Horde did not return a request id: {response.text[:500]}")

    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL)
        check = requests.get(
            f"{API}/generate/check/{request_id}",
            headers=HEADERS,
            timeout=(CONNECT_TIMEOUT, 30),
        )
        check.raise_for_status()
        state = check.json()

        if state.get("faulted"):
            raise RuntimeError(f"AI Horde generation faulted: {state}")
        if state.get("done"):
            result = requests.get(
                f"{API}/generate/status/{request_id}",
                headers=HEADERS,
                timeout=(CONNECT_TIMEOUT, 60),
            )
            result.raise_for_status()
            generations = result.json().get("generations") or []
            if not generations or not generations[0].get("img"):
                raise RuntimeError(f"AI Horde completed without an image: {result.text[:500]}")

            image_response = requests.get(
                generations[0]["img"],
                headers={"User-Agent": HEADERS["Client-Agent"]},
                timeout=(CONNECT_TIMEOUT, 120),
            )
            image_response.raise_for_status()
            image = Image.open(BytesIO(image_response.content)).convert("RGB")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, "JPEG", quality=94, optimize=True)
            return output_path

    raise TimeoutError(
        f"AI Horde request {request_id} was still queued/processing after "
        f"{MAX_WAIT_SECONDS} seconds"
    )

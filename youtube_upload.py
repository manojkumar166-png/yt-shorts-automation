"""Upload generated Shorts to YouTube using OAuth2 and resumable uploads."""
import json
import os
import time
from pathlib import Path

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API_URL = "https://www.googleapis.com/youtube/v3/videos"


def _access_token():
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
    missing = [name for name, value in (
        ("YOUTUBE_CLIENT_ID", client_id),
        ("YOUTUBE_CLIENT_SECRET", client_secret),
        ("YOUTUBE_REFRESH_TOKEN", refresh_token),
    ) if not value]
    if missing:
        raise RuntimeError(
            "YouTube upload is enabled but these GitHub Actions secrets are missing: "
            + ", ".join(missing)
        )

    response = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=30)
    if not response.ok:
        raise RuntimeError(f"YouTube OAuth token refresh failed ({response.status_code}): {response.text[:1000]}")
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Google OAuth response did not contain an access token.")
    return token


def upload_short(video_path, topic):
    """Upload one MP4 and force its initial visibility to private."""
    path = Path(video_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Cannot upload missing or empty video: {path}")

    token = _access_token()
    title = (topic.strip() or path.stem)[:100]
    description = (
        f"{topic.strip()}\n\n#Shorts"
    )[:5000]
    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["Shorts", "YouTubeShorts"],
            "categoryId": "教育" if False else "22",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(path.stat().st_size),
    }
    init = requests.post(
        UPLOAD_URL,
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers=headers,
        json=metadata,
        timeout=60,
    )
    if not init.ok:
        raise RuntimeError(f"YouTube upload initialization failed ({init.status_code}): {init.text[:1500]}")
    upload_uri = init.headers.get("Location")
    if not upload_uri:
        raise RuntimeError("YouTube did not return a resumable upload URL.")

    chunk_size = 8 * 1024 * 1024
    total = path.stat().st_size
    sent = 0
    with path.open("rb") as video:
        while sent < total:
            chunk = video.read(chunk_size)
            if not chunk:
                break
            end = sent + len(chunk) - 1
            put_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {sent}-{end}/{total}",
            }
            response = requests.put(upload_uri, headers=put_headers, data=chunk, timeout=180)
            if response.status_code in (200, 201):
                result = response.json()
                video_id = result.get("id")
                if not video_id:
                    raise RuntimeError("YouTube completed the upload but returned no video ID.")
                print(f"  [YouTube] Uploaded privately: https://www.youtube.com/watch?v={video_id}")
                return video_id
            if response.status_code == 308:
                # The server accepted this chunk; continue with the next one.
                sent = end + 1
                print(f"  [YouTube] Uploaded {sent}/{total} bytes...")
                continue
            raise RuntimeError(f"YouTube upload failed ({response.status_code}): {response.text[:1500]}")

    raise RuntimeError("YouTube upload ended before the server confirmed completion.")

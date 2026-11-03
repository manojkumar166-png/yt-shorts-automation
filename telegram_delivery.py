"""Deliver rendered Shorts to Telegram, compressing oversized uploads safely."""
import os
import subprocess
import tempfile
from pathlib import Path

import requests

# Stay comfortably below Telegram Bot API's hosted sendVideo upload limit.
TELEGRAM_MAX_BYTES = 48 * 1024 * 1024


def _telegram_ready_video(video_path):
    """Return (path_to_upload, temporary_path_or_none). Preserve original artifact."""
    source = Path(video_path)
    size = source.stat().st_size
    if size <= TELEGRAM_MAX_BYTES:
        print(f"  [Telegram] Video size {size / (1024 * 1024):.1f} MiB; no compression needed.", flush=True)
        return str(source), None

    print(
        f"  [Telegram] Video is {size / (1024 * 1024):.1f} MiB; "
        "compressing an upload copy to fit Telegram (original remains unchanged)...",
        flush=True,
    )
    fd, temp_path = tempfile.mkstemp(suffix=".mp4", prefix="telegram_")
    os.close(fd)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(source),
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "veryfast",
                "-b:v", "4200k", "-maxrate", "4500k", "-bufsize", "9000k",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                temp_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        compressed_size = os.path.getsize(temp_path)
        if compressed_size > TELEGRAM_MAX_BYTES:
            raise RuntimeError(
                f"Compressed video is still too large ({compressed_size / (1024 * 1024):.1f} MiB)."
            )
        print(
            f"  [Telegram] Upload copy ready: {compressed_size / (1024 * 1024):.1f} MiB.",
            flush=True,
        )
        return temp_path, temp_path
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def send_video(video_path, bot_token, chat_id, caption):
    upload_path, temporary_path = _telegram_ready_video(video_path)
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    try:
        with open(upload_path, "rb") as video:
            response = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"video": (Path(video_path).name, video, "video/mp4")},
                timeout=(30, 600),
            )
        if response.status_code == 413:
            raise RuntimeError(
                "Telegram still rejected the upload as too large (HTTP 413). "
                "The original MP4 is preserved in the GitHub Actions artifact."
            )
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram rejected the video: {result}")
        return result["result"]
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass

"""Deliver rendered Shorts to Telegram with size-aware, high-quality compression."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests

# Telegram's hosted Bot API upload ceiling is 50 MB (decimal). Keep a generous
# safety margin for multipart overhead and provider-side size accounting.
TELEGRAM_MAX_BYTES = 47_000_000
TARGET_UPLOAD_BYTES = 44_000_000
AUDIO_BITRATE_KBPS = 128


def _duration_seconds(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True, capture_output=True, text=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError(f"Could not determine a valid duration for {path}.")
    return duration


def _encode_upload_copy(source, destination, video_bitrate_kbps):
    """Encode an upload-only H.264 copy; never modify the source artifact."""
    command = [
        "ffmpeg", "-y", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "slow",
        "-b:v", f"{video_bitrate_kbps}k",
        "-maxrate", f"{int(video_bitrate_kbps * 1.12)}k",
        "-bufsize", f"{int(video_bitrate_kbps * 2.24)}k",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", f"{AUDIO_BITRATE_KBPS}k",
        "-movflags", "+faststart",
        str(destination),
    ]
    return subprocess.run(
        command, check=True, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, text=True,
    )


def _telegram_ready_video(video_path):
    """Return (upload_path, temporary_path_or_none), preserving original video."""
    source = Path(video_path)
    if not source.is_file() or source.stat().st_size == 0:
        raise RuntimeError(f"Video is missing or empty: {source}")

    original_size = source.stat().st_size
    if original_size <= TELEGRAM_MAX_BYTES:
        print(
            f"  [Telegram] {original_size / 1_000_000:.1f} MB; no compression needed.",
            flush=True,
        )
        return str(source), None

    duration = _duration_seconds(source)
    # Reserve room for audio, container overhead, and multipart upload framing.
    total_kbps = (TARGET_UPLOAD_BYTES * 8 / duration) / 1000
    video_kbps = max(350, int(total_kbps - AUDIO_BITRATE_KBPS - 100))

    print(
        f"  [Telegram] Original is {original_size / 1_000_000:.1f} MB "
        f"({duration:.1f}s). Creating a high-quality upload copy; original is preserved.",
        flush=True,
    )

    fd, temp_path = tempfile.mkstemp(suffix=".mp4", prefix="telegram_")
    os.close(fd)
    try:
        last_size = None
        for attempt in range(1, 5):
            Path(temp_path).unlink(missing_ok=True)
            try:
                _encode_upload_copy(source, temp_path, video_kbps)
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or "")[-3000:]
                raise RuntimeError(f"FFmpeg compression failed: {detail}") from exc

            last_size = os.path.getsize(temp_path)
            print(
                f"  [Telegram] Compression pass {attempt}: "
                f"{last_size / 1_000_000:.1f} MB at {video_kbps} kbps video.",
                flush=True,
            )
            if last_size <= TELEGRAM_MAX_BYTES:
                # Verify the upload copy is a readable MP4 with a video stream.
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=codec_name,width,height",
                     "-of", "json", temp_path],
                    check=True, capture_output=True, text=True,
                )
                streams = json.loads(probe.stdout).get("streams", [])
                if not streams:
                    raise RuntimeError("Compressed upload has no readable video stream.")
                print(
                    f"  [Telegram] Ready: {last_size / 1_000_000:.1f} MB "
                    f"(original {original_size / 1_000_000:.1f} MB).",
                    flush=True,
                )
                return temp_path, temp_path

            # Recalculate downwards based on the measured file size, with a
            # safety margin so a variable-bitrate encode cannot sit on the limit.
            ratio = (TARGET_UPLOAD_BYTES / last_size) * 0.94
            video_kbps = max(300, int(video_kbps * min(ratio, 0.90)))

        raise RuntimeError(
            f"Could not compress video below Telegram's safe upload limit after "
            f"4 passes (last size {last_size / 1_000_000:.1f} MB). "
            "The original remains available in the GitHub Actions artifact."
        )
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise


def send_video(video_path, bot_token, chat_id, caption):
    upload_path, temporary_path = _telegram_ready_video(video_path)
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    try:
        for attempt in range(1, 4):
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
                        "Telegram rejected the upload as too large (HTTP 413), "
                        "even after size-aware compression. The original MP4 is "
                        "preserved in the GitHub Actions artifact."
                    )
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    retry_after = 0
                    try:
                        retry_after = int(response.json().get("parameters", {}).get("retry_after", 0))
                    except (ValueError, AttributeError):
                        pass
                    delay = max(retry_after, attempt * 5)
                    print(
                        f"  [Telegram] Temporary HTTP {response.status_code}; "
                        f"retrying in {delay}s ({attempt}/3)...",
                        flush=True,
                    )
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                result = response.json()
                if not result.get("ok"):
                    raise RuntimeError(f"Telegram rejected the video: {result}")
                return result["result"]
            except (requests.Timeout, requests.ConnectionError):
                if attempt >= 3:
                    raise
                delay = attempt * 5
                print(
                    f"  [Telegram] Network error; retrying in {delay}s ({attempt}/3)...",
                    flush=True,
                )
                time.sleep(delay)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)

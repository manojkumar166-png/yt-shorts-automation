"""Deliver rendered Shorts to a Telegram chat using the Bot API."""
import requests


def send_video(video_path, bot_token, chat_id, caption):
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    with open(video_path, "rb") as video:
        response = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={"video": (video_path.rsplit("/", 1)[-1], video, "video/mp4")},
            timeout=(30, 600),
        )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram rejected the video: {result}")
    return result["result"]

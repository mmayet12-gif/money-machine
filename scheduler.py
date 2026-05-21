#!/usr/bin/env python3
"""
Scheduler — runs via Windows Task Scheduler every 15 minutes.

Checks the upload queue, uploads any due videos, sends notifications.
One run, one pass, then exits. Never loops.

Kill switch: if C:\\money-machine\\PAUSE exists, does nothing.
"""
from __future__ import annotations

import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"C:\money-machine")
PAUSE_FILE = ROOT / "PAUSE"
QUEUE_FILE = ROOT / "config" / "upload_queue.json"
NOTIFICATION_LOG = ROOT / "logs" / "notifications.log"
UPLOAD_LOG = ROOT / "logs" / "uploads.log"

MAX_RETRIES = 3
RETRY_DELAY_MINUTES = 30


def log(msg: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    try:
        UPLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
        with UPLOAD_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_queue() -> dict:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"WARNING: Queue file corrupt: {e}")
    return {"queue": []}


def save_queue(data: dict) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def log_notification(title: str, body: str, url: str | None = None) -> None:
    NOTIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "body": body,
        "url": url,
    }
    with NOTIFICATION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def send_toast(title: str, body: str, url: str | None = None) -> None:
    try:
        from winotify import Notification, audio

        toast = Notification(
            app_id="Money Machine",
            title=title,
            msg=body,
            duration="long",
        )
        if url:
            toast.add_actions(label="Open YouTube Studio", launch=url)
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return
    except ImportError:
        pass

    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            body,
            duration=10,
            threaded=True,
            callback_on_click=lambda: webbrowser.open(url) if url else None,
        )
        return
    except ImportError:
        pass

    log(f"TOAST (no toast library): {title} — {body}")


def send_discord(title: str, body: str, url: str | None = None) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
        return
    try:
        import requests
        embed = {
            "title": title,
            "description": body,
            "color": 0x00FF00 if "Uploaded" in title else 0xFF0000,
        }
        if url:
            embed["url"] = url
            embed["description"] += f"\n\n[Review and publish]({url})"
        payload = {"embeds": [embed]}
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        log(f"Discord notification failed (non-fatal): {e}")


def notify_success(title: str, studio_url: str) -> None:
    toast_title = f"Uploaded: {title}"
    toast_body = "Click to review in YouTube Studio"
    log_notification(toast_title, toast_body, studio_url)
    send_toast(toast_title, toast_body, studio_url)
    send_discord(toast_title, toast_body, studio_url)


def notify_failure(title: str, error: str) -> None:
    toast_title = f"Upload failed: {title}"
    toast_body = error[:200]
    log_notification(toast_title, toast_body)
    send_toast(toast_title, toast_body)
    send_discord(toast_title, toast_body)


def do_upload(entry: dict) -> dict:
    sys.path.insert(0, str(ROOT))
    from youtube_uploader import upload_video, find_metadata

    video_path = Path(entry["video_path"])
    if not video_path.exists():
        raise FileNotFoundError(f"Video file missing: {video_path}")

    if entry.get("metadata_path") and Path(entry["metadata_path"]).exists():
        metadata = json.loads(Path(entry["metadata_path"]).read_text(encoding="utf-8"))
    else:
        metadata = find_metadata(video_path)

    is_short = entry.get("kind") == "short"
    return upload_video(video_path, metadata, is_short=is_short)


def process_queue() -> int:
    data = load_queue()
    now = datetime.now()

    due = [
        q for q in data["queue"]
        if q["status"] == "pending"
        and datetime.fromisoformat(q["scheduled_for"]) <= now
    ]

    if not due:
        log("Nothing due. Exiting.")
        return 0

    log(f"{len(due)} video(s) due for upload.")

    for entry in due:
        video_name = Path(entry["video_path"]).stem
        log(f"Uploading: {video_name}")

        entry["status"] = "uploading"
        save_queue(data)

        try:
            result = do_upload(entry)
            entry["status"] = "uploaded"
            entry["uploaded_at"] = result["uploaded_at"]
            entry["video_id"] = result["video_id"]
            entry["studio_url"] = result["studio_url"]
            entry["error"] = None
            save_queue(data)

            log(f"SUCCESS: {video_name} -> {result['video_id']}")
            notify_success(result["title"], result["studio_url"])

        except Exception as e:
            entry["retry_count"] = entry.get("retry_count", 0) + 1
            entry["error"] = str(e)

            if entry["retry_count"] < MAX_RETRIES:
                retry_time = now + timedelta(minutes=RETRY_DELAY_MINUTES)
                entry["status"] = "pending"
                entry["scheduled_for"] = retry_time.isoformat()
                log(f"FAILED (retry {entry['retry_count']}/{MAX_RETRIES}): {e}")
                log(f"  Rescheduled for {retry_time.strftime('%H:%M')}")
            else:
                entry["status"] = "failed"
                log(f"FAILED permanently after {MAX_RETRIES} retries: {e}")
                notify_failure(video_name.replace("_", " "), str(e))

            save_queue(data)

    return 0


def main() -> int:
    # Kill switch — checked BEFORE loading the queue
    if PAUSE_FILE.exists():
        log("PAUSED — C:\\money-machine\\PAUSE exists. Exiting.")
        return 0

    try:
        return process_queue()
    except Exception as e:
        log(f"SCHEDULER CRASH: {e}")
        notify_failure("Scheduler", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())

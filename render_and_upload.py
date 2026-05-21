#!/usr/bin/env python3
"""
Render watcher + auto-uploader.

Watches the output/videos folder for newly rendered videos and uploads them
to YouTube as PRIVATE as they appear. Respects YouTube's daily upload limit.

Usage:
    python render_and_upload.py          # watch and upload as videos finish
    python render_and_upload.py --once   # upload whatever is ready now, then exit
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\money-machine")
VIDEOS_DIR = ROOT / "output" / "videos"
UPLOAD_LOG = ROOT / "logs" / "uploads.log"
PROGRESS_FILE = ROOT / "output" / "logs" / "progress.json"

sys.path.insert(0, str(ROOT))
from youtube_uploader import (
    load_credentials,
    build_service,
    upload_video,
    find_metadata,
    detect_short,
    log_upload,
)


def get_uploaded_titles() -> set:
    uploaded = set()
    if UPLOAD_LOG.exists():
        for line in UPLOAD_LOG.read_text(encoding="utf-8").strip().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("result") == "success":
                    uploaded.add(entry.get("title", ""))
            except json.JSONDecodeError:
                continue
    return uploaded


def get_ready_videos() -> list[Path]:
    """Get videos that are fully rendered (exist in progress.json as completed)."""
    if not PROGRESS_FILE.exists():
        return []

    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    completed = progress.get("completed", {})

    ready = []
    for idx, info in completed.items():
        video_path = Path(info.get("video", ""))
        if video_path.exists() and video_path.stat().st_size > 100_000:
            ready.append(video_path)

    return sorted(ready)


def upload_batch(watch_mode: bool = False) -> int:
    """Upload all ready videos that haven't been uploaded yet."""
    print("Verifying YouTube credentials...")
    try:
        creds = load_credentials()
        service = build_service(creds)
        resp = service.channels().list(mine=True, part="snippet").execute()
        channel = resp["items"][0]["snippet"]["title"]
        print(f"  Channel: {channel}\n")
    except Exception as e:
        print(f"ERROR: Credentials failed: {e}")
        print("Fix: python youtube_uploader.py --authorize")
        return 1

    uploaded_titles = get_uploaded_titles()
    uploaded_count = 0
    failed_count = 0

    while True:
        ready = get_ready_videos()
        pending = []
        for v in ready:
            meta = find_metadata(v)
            title = meta.get("title", v.stem)
            if title not in uploaded_titles:
                pending.append((v, meta, title))

        if not pending:
            if watch_mode:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No new videos ready. Waiting 60s...", flush=True)
                time.sleep(60)
                continue
            else:
                print("No pending uploads.")
                break

        for video_path, metadata, title in pending:
            is_short = detect_short(video_path)
            size_mb = video_path.stat().st_size / 1_048_576

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Uploading: {title}")
            print(f"  Size: {size_mb:.1f} MB | Type: {'Short' if is_short else 'Long-form'}")

            try:
                result = upload_video(video_path, metadata, is_short=is_short)
                uploaded_count += 1
                uploaded_titles.add(title)
                print(f"  OK -> {result['url']}\n")
                time.sleep(10)

            except Exception as e:
                error_msg = str(e)
                failed_count += 1
                print(f"  FAILED: {error_msg}\n")

                log_upload({
                    "timestamp": datetime.now().isoformat(),
                    "title": title,
                    "file_size_mb": round(size_mb, 1),
                    "result": "failed",
                    "error": error_msg,
                })

                if "uploadLimitExceeded" in error_msg or "exceeded the number of videos" in error_msg:
                    print(f"\nYouTube daily upload limit reached after {uploaded_count} uploads.")
                    print("The limit resets in ~24 hours. Run this again tomorrow.")
                    if watch_mode:
                        print("Waiting 4 hours before retrying...")
                        time.sleep(14400)
                        continue
                    return 0

                if "quota" in error_msg.lower():
                    print("API quota exceeded. Try again tomorrow.")
                    return 0

                time.sleep(5)

        if not watch_mode:
            break

    print(f"\n{'='*50}")
    print(f"  Uploaded: {uploaded_count}  |  Failed: {failed_count}")
    print(f"{'='*50}")
    if uploaded_count > 0:
        print(f"  Review at: https://studio.youtube.com")
    return 0


def main():
    import argparse
    p = argparse.ArgumentParser(description="Watch for rendered videos and upload to YouTube")
    p.add_argument("--once", action="store_true", help="Upload what's ready now, then exit")
    args = p.parse_args()

    watch_mode = not args.once
    if watch_mode:
        print("=== RENDER WATCHER + AUTO-UPLOADER ===")
        print("Watching for new videos and uploading as they finish...")
        print("Press Ctrl+C to stop.\n")

    return upload_batch(watch_mode=watch_mode)


if __name__ == "__main__":
    sys.exit(main())

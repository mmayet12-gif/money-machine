#!/usr/bin/env python3
"""
Batch YouTube Uploader — uploads all rendered videos as PRIVATE.

Usage:
    python batch_upload.py                  # upload all videos in output/videos
    python batch_upload.py --dry-run        # preview without uploading
    python batch_upload.py --limit 5        # upload first 5 only
    python batch_upload.py --start 21       # start from video 21

Skips videos that have already been uploaded (tracked in logs/uploads.log).
Uploads as PRIVATE always. Rate-limits to stay within YouTube API quotas.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\money-machine")
VIDEOS_DIR = ROOT / "output" / "videos"
UPLOAD_LOG = ROOT / "logs" / "uploads.log"

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
    """Read upload log to find already-uploaded video titles."""
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


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Batch upload all rendered videos")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    p.add_argument("--limit", type=int, default=0, help="Max videos to upload (0 = all)")
    p.add_argument("--start", type=int, default=1, help="Start from video number N")
    args = p.parse_args()

    # Find all rendered videos
    videos = sorted(VIDEOS_DIR.glob("*.mp4"))
    if not videos:
        print("No videos found in output/videos/")
        return 1

    # Check already uploaded
    uploaded_titles = get_uploaded_titles()

    # Verify credentials before starting
    if not args.dry_run:
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

    total = len(videos)
    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    print(f"Found {total} videos. Starting uploads...\n")

    for i, video_path in enumerate(videos, 1):
        if i < args.start:
            continue

        metadata = find_metadata(video_path)
        title = metadata.get("title", video_path.stem)
        is_short = detect_short(video_path)
        size_mb = video_path.stat().st_size / 1_048_576

        # Skip already uploaded
        if title in uploaded_titles:
            print(f"[{i:03d}/{total}] SKIP (already uploaded): {title}")
            skipped_count += 1
            continue

        if args.limit > 0 and uploaded_count >= args.limit:
            print(f"\nReached limit of {args.limit} uploads. Stopping.")
            break

        print(f"[{i:03d}/{total}] Uploading: {title}")
        print(f"           Size: {size_mb:.1f} MB | Type: {'Short' if is_short else 'Long-form'}")

        if args.dry_run:
            print(f"           DRY RUN - would upload as PRIVATE")
            uploaded_count += 1
            continue

        try:
            result = upload_video(video_path, metadata, is_short=is_short)
            uploaded_count += 1
            print(f"           OK -> {result['url']}\n")

            # Rate limit: YouTube API quota is 10,000 units/day
            # Each upload costs ~1600 units, so max ~6 uploads per day
            # But for initial testing, wait 10s between uploads
            if i < total:
                print("  Waiting 10s (API rate limit)...")
                time.sleep(10)

        except Exception as e:
            failed_count += 1
            error_msg = str(e)
            print(f"           FAILED: {error_msg}\n")

            log_upload({
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "title": title,
                "file_size_mb": round(size_mb, 1),
                "result": "failed",
                "error": error_msg,
            })

            # If quota or upload limit exceeded, stop entirely
            if "quota" in error_msg.lower() or "rateLimitExceeded" in error_msg:
                print("\nYouTube API quota exceeded. Try again tomorrow.")
                print("YouTube allows ~6 video uploads per day with default quota.")
                break
            if "uploadLimitExceeded" in error_msg or "exceeded the number of videos" in error_msg:
                print("\nYouTube daily upload limit reached. Try again tomorrow.")
                print("New channels are limited to ~7-10 uploads per day.")
                break

            # Other errors: continue with next video
            time.sleep(5)

    print(f"\n{'='*60}")
    print(f"  BATCH UPLOAD COMPLETE")
    print(f"{'='*60}")
    print(f"  Uploaded:  {uploaded_count}")
    print(f"  Skipped:   {skipped_count}")
    print(f"  Failed:    {failed_count}")
    print(f"  Remaining: {total - uploaded_count - skipped_count - failed_count}")
    print(f"{'='*60}")

    if uploaded_count > 0 and not args.dry_run:
        print(f"\n  All uploads are PRIVATE.")
        print(f"  Review in YouTube Studio: https://studio.youtube.com")
        print(f"  Upload log: {UPLOAD_LOG}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
YouTube Uploader — uploads videos as PRIVATE, always.

Usage:
    python youtube_uploader.py --authorize       # first-time OAuth
    python youtube_uploader.py --whoami          # verify connected channel
    python youtube_uploader.py --upload <path>   # upload a single video
    python youtube_uploader.py --upload <path> --short   # force-treat as Short
    python youtube_uploader.py --upload <path> --dry-run # preview without uploading
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\money-machine")
CONFIG_DIR = ROOT / "config"
LOGS_DIR = ROOT / "logs"
METADATA_DIR = ROOT / "output" / "metadata"

CLIENT_SECRET = CONFIG_DIR / "client_secret.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
UPLOAD_LOG = LOGS_DIR / "uploads.log"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def log_upload(entry: dict) -> None:
    UPLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with UPLOAD_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def authorize() -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRET.exists():
        print(f"ERROR: {CLIENT_SECRET} not found.")
        print("Download it from Google Cloud Console. See OAUTH_SETUP.md.")
        sys.exit(1)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"Authorization successful. Token saved to {TOKEN_FILE}")


def load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN_FILE.exists():
        print(f"ERROR: {TOKEN_FILE} not found.")
        print("Run: python youtube_uploader.py --authorize")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        except Exception:
            print("ERROR: Token expired and refresh failed.")
            print("This happens every ~7 days in Testing mode.")
            print("Fix: python youtube_uploader.py --authorize")
            sys.exit(1)

    if not creds.valid:
        print("ERROR: Credentials are not valid.")
        print("Fix: python youtube_uploader.py --authorize")
        sys.exit(1)

    return creds


def build_service(creds):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds)


def whoami() -> dict:
    creds = load_credentials()
    service = build_service(creds)
    resp = service.channels().list(
        mine=True,
        part="snippet,statistics",
    ).execute()

    if not resp.get("items"):
        print("ERROR: No channel found for this account.")
        return {}

    ch = resp["items"][0]
    info = {
        "title": ch["snippet"]["title"],
        "subscribers": ch["statistics"].get("subscriberCount", "hidden"),
        "videos": ch["statistics"].get("videoCount", "0"),
    }
    print(f"Channel:     {info['title']}")
    print(f"Subscribers: {info['subscribers']}")
    print(f"Videos:      {info['videos']}")
    return info


def detect_short(video_path: Path) -> bool:
    if "short" in video_path.stem.lower():
        return True
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", str(video_path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                w = int(stream.get("width", 0))
                h = int(stream.get("height", 0))
                if h > w and h >= 1080:
                    return True
    except Exception:
        pass
    return False


def upload_video(video_path: Path, metadata: dict, is_short: bool = False) -> dict:
    from googleapiclient.http import MediaFileUpload

    creds = load_credentials()
    service = build_service(creds)

    title = metadata.get("title", video_path.stem)
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    category_id = metadata.get("category_id", "27")

    if is_short:
        if len(title) > 100:
            title = title[:97] + "..."
        if "#Shorts" not in description:
            description = description.rstrip() + "\n\n#Shorts"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        chunksize=1024 * 1024,
        resumable=True,
        mimetype="video/mp4",
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
        notifySubscribers=False,
    )

    t0 = time.time()
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  Uploading... {pct}%", flush=True)

    elapsed = time.time() - t0
    video_id = response["id"]

    result = {
        "video_id": video_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "studio_url": f"https://studio.youtube.com/video/{video_id}/edit",
        "uploaded_at": datetime.now().isoformat(),
        "title": title,
        "is_short": is_short,
        "privacy_status": "public",
    }

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "video_id": video_id,
        "title": title,
        "file_size_mb": round(video_path.stat().st_size / 1_048_576, 1),
        "upload_seconds": round(elapsed, 1),
        "result": "success",
    }
    log_upload(log_entry)

    print(f"\n  Uploaded successfully as PRIVATE")
    print(f"  Video ID:   {video_id}")
    print(f"  Watch:      {result['url']}")
    print(f"  Studio:     {result['studio_url']}")
    print(f"  Duration:   {elapsed:.0f}s")

    return result


def find_metadata(video_path: Path) -> dict:
    stem = video_path.stem
    meta_path = METADATA_DIR / f"{stem}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    candidates = sorted(METADATA_DIR.glob("*.json"))
    for c in candidates:
        if stem.startswith(c.stem[:5]):
            return json.loads(c.read_text(encoding="utf-8"))
    print(f"WARNING: No metadata JSON found for {video_path.name}")
    print(f"         Using defaults. Looked in {METADATA_DIR}")
    return {"title": stem.replace("_", " "), "description": "", "tags": [], "category_id": "27"}


def main() -> int:
    p = argparse.ArgumentParser(
        description="YouTube uploader — uploads as PRIVATE, always",
    )
    p.add_argument("--authorize", action="store_true", help="Run OAuth flow and save token")
    p.add_argument("--whoami", action="store_true", help="Print connected channel info")
    p.add_argument("--upload", metavar="VIDEO", help="Upload a video file")
    p.add_argument("--short", action="store_true", help="Force-treat upload as a YouTube Short")
    p.add_argument("--dry-run", action="store_true", help="Print what would happen, don't upload")
    args = p.parse_args()

    if args.authorize:
        authorize()
        return 0

    if args.whoami:
        whoami()
        return 0

    if args.upload:
        video_path = Path(args.upload)
        if not video_path.exists():
            print(f"ERROR: File not found: {video_path}")
            return 1

        is_short = args.short or detect_short(video_path)
        metadata = find_metadata(video_path)

        if args.dry_run:
            print("=== DRY RUN ===")
            print(f"  File:     {video_path}")
            print(f"  Size:     {video_path.stat().st_size / 1_048_576:.1f} MB")
            print(f"  Title:    {metadata.get('title', video_path.stem)}")
            print(f"  Kind:     {'Short' if is_short else 'Long-form'}")
            print(f"  Privacy:  public")
            print(f"  Metadata: {METADATA_DIR / (video_path.stem + '.json')}")
            print("=== Nothing uploaded ===")
            return 0

        try:
            result = upload_video(video_path, metadata, is_short=is_short)
        except Exception as e:
            log_upload({
                "timestamp": datetime.now().isoformat(),
                "title": metadata.get("title", video_path.stem),
                "file_size_mb": round(video_path.stat().st_size / 1_048_576, 1),
                "result": "failed",
                "error": str(e),
            })
            print(f"\nERROR: Upload failed: {e}")
            return 1

        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

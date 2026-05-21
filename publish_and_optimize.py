#!/usr/bin/env python3
"""
publish_and_optimize.py
- Makes all PRIVATE videos PUBLIC on all 3 channels
- Updates titles, descriptions, tags for SEO
- Works with existing token.json files (no re-auth needed)
"""
import os, sys, time, json
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CHANNELS = [
    {
        "name": "Mo Money",
        "token": Path(r"C:\money-machine\config\token.json"),
    },
    {
        "name": "Bright Side",
        "token": Path(r"C:\bright-side\config\token.json"),
    },
    {
        "name": "MotiversityZA",
        "token": Path(r"C:\motivation-channel\config\token.json"),
    },
]

# ── SEO data by channel ────────────────────────────────────────────────────────

CHANNEL_SEO = {
    "Mo Money": {
        "tags": [
            "personal finance", "money tips", "budgeting", "financial freedom",
            "wealth building", "save money", "invest money", "financial advice 2026",
            "money management", "passive income", "side hustle", "financial independence",
            "how to get rich", "investing for beginners", "make money online",
        ],
        "category_id": "27",
        "footer": (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰 Mo Money — daily financial tips that actually work.\n"
            "Subscribe for new videos every day: https://youtube.com/@moe12ism\n\n"
            "#PersonalFinance #MoneyTips #FinancialFreedom #PassiveIncome #Investing2026"
        ),
    },
    "Bright Side": {
        "tags": [
            "facts", "amazing facts", "did you know", "science facts", "mind blowing facts",
            "incredible facts", "interesting facts 2026", "top facts", "educational",
            "amazing animals", "space facts", "history facts", "nature facts",
            "bright side", "knowledge", "learn something new",
        ],
        "category_id": "27",
        "footer": (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 Bright Side — incredible facts about the world around us.\n"
            "New video every day: https://youtube.com/@moe12ism\n\n"
            "#Facts #AmazingFacts #DidYouKnow #Education #Science"
        ),
    },
    "MotiversityZA": {
        "tags": [
            "motivation", "motivational speech", "motivation 2026", "success mindset",
            "how to be successful", "self improvement", "mindset", "discipline",
            "growth mindset", "productivity tips", "success habits", "life advice",
            "personal development", "motivational video", "achieve your goals",
        ],
        "category_id": "26",
        "footer": (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 MotiversityZA — fuel your mindset every single day.\n"
            "Subscribe: https://youtube.com/@motiversityza\n\n"
            "#Motivation #Mindset #Success #SelfImprovement #Discipline2026"
        ),
    },
}

DESCRIPTION_HOOKS = [
    "Most people never learn this — but once you do, everything changes.",
    "This is one of the most important things you'll watch today.",
    "Share this with someone who needs to see it.",
    "Thousands of people have already applied this — here's what they found.",
    "If you take one thing from this video, let it be this.",
]


def get_service(token_path: Path, channel_name: str):
    if not token_path.exists():
        print(f"  ⚠ No token for {channel_name} — skipping")
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
        return build("youtube", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"  ⚠ Auth failed for {channel_name}: {e}")
        return None


def build_description(title: str, channel_name: str) -> str:
    hook = DESCRIPTION_HOOKS[hash(title) % len(DESCRIPTION_HOOKS)]
    footer = CHANNEL_SEO[channel_name]["footer"]
    timestamps = (
        "⏱️ CHAPTERS\n"
        "0:00 — Introduction\n"
        "0:20 — Main breakdown\n"
        "1:00 — Key insight\n"
        "1:45 — Takeaways\n"
        "2:10 — What to do next\n"
    )
    return (
        f"{hook}\n\n"
        f"{title} — in this video we break down exactly what you need to know, "
        f"step by step, with no fluff.\n\n"
        f"{timestamps}"
        f"\n🔔 Subscribe and hit the bell so you never miss an upload.\n"
        f"{footer}"
    )


def optimize_title(title: str) -> str:
    """Add year if title is short enough and doesn't already have it."""
    if "2026" not in title and len(title) <= 55:
        return f"{title} (2026)"
    return title


def process_channel(ch: dict):
    name = ch["name"]
    seo = CHANNEL_SEO[name]
    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"{'='*55}")

    service = get_service(ch["token"], name)
    if not service:
        return

    # Fetch all videos via uploads playlist (most reliable method)
    print("  Fetching videos...")
    videos = []
    try:
        ch_resp = service.channels().list(mine=True, part="contentDetails").execute()
        uploads_id = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        page = None
        while True:
            pl_resp = service.playlistItems().list(
                part="snippet", playlistId=uploads_id, maxResults=50,
                **({} if not page else {"pageToken": page})
            ).execute()
            for item in pl_resp.get("items", []):
                vid_id = item["snippet"]["resourceId"]["videoId"]
                videos.append({"id": vid_id, "title": item["snippet"]["title"]})
            page = pl_resp.get("nextPageToken")
            if not page:
                break
    except Exception as e:
        print(f"  Playlist fetch failed: {e}")

    if not videos:
        print("  No videos to process.")
        return

    print(f"  Found {len(videos)} videos")

    # Batch get status for all videos
    all_ids = [v["id"] for v in videos]
    id_to_privacy = {}
    for i in range(0, len(all_ids), 50):
        chunk = all_ids[i:i+50]
        try:
            vr = service.videos().list(part="status", id=",".join(chunk)).execute()
            for item in vr.get("items", []):
                id_to_privacy[item["id"]] = item["status"]["privacyStatus"]
        except Exception as e:
            print(f"  Status fetch failed: {e}")

    private_count = sum(1 for vid in videos if id_to_privacy.get(vid["id"]) == "private")
    print(f"  Private: {private_count} | Will optimize all: {len(videos)}")

    success = 0
    published = 0
    for i, vid in enumerate(videos):
        vid_id = vid["id"]
        title = vid["title"]
        current_privacy = id_to_privacy.get(vid_id, "unknown")

        new_title = optimize_title(title)
        new_desc = build_description(title, name)
        new_tags = seo["tags"]

        status_part = {}
        if current_privacy == "private":
            status_part = {"privacyStatus": "public"}

        print(f"  [{i+1}/{len(videos)}] {title[:50]}", end="")
        if current_privacy == "private":
            print(" → PUBLISHING", end="")

        try:
            # Update snippet
            service.videos().update(
                part="snippet,status",
                body={
                    "id": vid_id,
                    "snippet": {
                        "title": new_title,
                        "description": new_desc,
                        "tags": new_tags,
                        "categoryId": seo["category_id"],
                        "defaultLanguage": "en",
                    },
                    "status": {
                        "privacyStatus": "public",
                        "selfDeclaredMadeForKids": False,
                    },
                }
            ).execute()
            success += 1
            if current_privacy == "private":
                published += 1
            print(" ✓")
        except Exception as e:
            print(f" FAILED: {e}")
            if "quotaExceeded" in str(e):
                print("  API quota exceeded — stopping this channel.")
                break
        time.sleep(0.5)

    print(f"\n  Done. Updated {success}/{len(videos)} videos. Published {published} private → public.")


def main():
    for ch in CHANNELS:
        process_channel(ch)
    print("\n\n✅ All channels processed.")


if __name__ == "__main__":
    main()

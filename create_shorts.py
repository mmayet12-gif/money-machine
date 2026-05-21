#!/usr/bin/env python3
"""
Shorts Creator — takes rendered videos and creates vertical 9:16 Shorts (under 60s).
Crops to vertical, trims to 55s, adds bold title overlay, saves to output/shorts/.
Then batch-uploads them all as YouTube Shorts.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\money-machine")
VIDEOS_DIR = ROOT / "output" / "videos"
SHORTS_DIR = ROOT / "output" / "shorts"
METADATA_DIR = ROOT / "output" / "metadata"
UPLOAD_LOG = ROOT / "logs" / "uploads.log"
PROGRESS_FILE = ROOT / "output" / "logs" / "progress.json"

sys.path.insert(0, str(ROOT))
from youtube_uploader import load_credentials, build_service, log_upload

FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
SHORT_DURATION = 55  # seconds
SHORT_W, SHORT_H = 1080, 1920


def get_video_duration(video_path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", str(video_path)],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                return float(s.get("duration", 0))
    except Exception:
        pass
    return 0.0


def sanitize_drawtext(text: str) -> str:
    """Escape text for ffmpeg drawtext filter."""
    text = text[:60]  # truncate
    text = text.replace("'", "’")  # smart quote
    text = text.replace(":", r"\:")
    text = text.replace(",", r"\,")
    text = re.sub(r"[^\w\s\-\.\!\?’\\]", "", text)
    return text


def create_short(video_path: Path, title: str, output_path: Path) -> bool:
    """Two-pass approach: crop+scale, then burn text via Pillow overlay frame."""
    from PIL import Image, ImageDraw, ImageFont
    import tempfile

    duration = get_video_duration(video_path)
    trim_dur = min(SHORT_DURATION, duration - 0.5) if duration > 5 else SHORT_DURATION

    crop_w, crop_h, crop_x = 607, 1080, 656  # center crop from 1920x1080

    # ── Pass 1: crop + scale to vertical, trim ──────────────────────────
    tmp_vertical = output_path.parent / f"_tmp_{output_path.stem}.mp4"
    cmd1 = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-t", str(trim_dur),
        "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:0,scale={SHORT_W}:{SHORT_H}:flags=lanczos",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(tmp_vertical),
    ]
    try:
        r1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=180)
        if not tmp_vertical.exists() or tmp_vertical.stat().st_size < 50_000:
            print(f"    Pass1 failed: {r1.stderr[-200:]}")
            return False
    except Exception as e:
        print(f"    Pass1 error: {e}")
        return False

    # ── Build title overlay image with Pillow ───────────────────────────
    overlay_path = output_path.parent / f"_ovr_{output_path.stem}.png"
    try:
        img = Image.new("RGBA", (SHORT_W, SHORT_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark bar behind title
        draw.rectangle([0, 130, SHORT_W, 380], fill=(0, 0, 0, 170))

        try:
            font_title = ImageFont.truetype(FONT_PATH, 64)
            font_sub = ImageFont.truetype(FONT_PATH, 32)
        except Exception:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        # Word-wrap title into 2 lines
        words = title.split()
        mid = max(1, len(words) // 2)
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:]) if len(words) > 1 else ""

        for ln_idx, ln in enumerate([line1, line2]):
            if not ln:
                continue
            ln = ln[:45]
            bbox = draw.textbbox((0, 0), ln, font=font_title)
            tw = bbox[2] - bbox[0]
            x = max(20, (SHORT_W - tw) // 2)
            y = 148 + ln_idx * 80
            # Shadow
            draw.text((x + 3, y + 3), ln, font=font_title, fill=(0, 0, 0, 200))
            draw.text((x, y), ln, font=font_title, fill=(255, 255, 255, 255))

        # Red SHORTS badge top-right
        draw.rectangle([SHORT_W - 190, 25, SHORT_W - 20, 80], fill=(220, 0, 0, 230))
        draw.text((SHORT_W - 182, 32), "#SHORTS", font=font_sub, fill=(255, 255, 255, 255))

        img.save(str(overlay_path), "PNG")
    except Exception as e:
        print(f"    Overlay build error: {e}")
        tmp_vertical.unlink(missing_ok=True)
        return False

    # ── Pass 2: overlay the title image onto the video ──────────────────
    ovr_fwd = str(overlay_path).replace("\\", "/")
    cmd2 = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(tmp_vertical),
        "-i", str(overlay_path),
        "-filter_complex", "overlay=0:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    try:
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=180)
        success = output_path.exists() and output_path.stat().st_size > 50_000
        if not success:
            print(f"    Pass2 failed: {r2.stderr[-200:]}")
    except Exception as e:
        print(f"    Pass2 error: {e}")
        success = False

    tmp_vertical.unlink(missing_ok=True)
    overlay_path.unlink(missing_ok=True)
    return success


def get_uploaded_titles() -> set:
    uploaded = set()
    if UPLOAD_LOG.exists():
        for line in UPLOAD_LOG.read_text(encoding="utf-8").strip().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("result") == "success":
                    uploaded.add(entry.get("title", ""))
            except Exception:
                continue
    return uploaded


def upload_short(service, video_path: Path, title: str, description: str, tags: list) -> dict:
    from googleapiclient.http import MediaFileUpload

    short_title = title if len(title) <= 97 else title[:94] + "..."
    short_desc = description + "\n\n#Shorts #PersonalFinance #MoneyTips #FinancialFreedom"

    body = {
        "snippet": {
            "title": short_title,
            "description": short_desc,
            "tags": tags + ["Shorts", "#Shorts"],
            "categoryId": "27",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video_path), chunksize=512*1024, resumable=True, mimetype="video/mp4")
    request = service.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)

    t0 = time.time()
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    {int(status.progress()*100)}%", end="\r", flush=True)

    elapsed = time.time() - t0
    video_id = response["id"]
    log_upload({
        "timestamp": datetime.now().isoformat(),
        "video_id": video_id,
        "title": short_title,
        "file_size_mb": round(video_path.stat().st_size / 1_048_576, 1),
        "upload_seconds": round(elapsed, 1),
        "result": "success",
        "type": "short",
    })
    return {"video_id": video_id, "url": f"https://youtube.com/shorts/{video_id}"}


def get_ready_videos() -> list[Path]:
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


def get_title_for_video(video_path: Path) -> str:
    stem = video_path.stem
    meta_path = METADATA_DIR / f"{stem}.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return meta.get("title", stem.replace("_", " "))
    # Try prefix match
    for m in sorted(METADATA_DIR.glob("*.json")):
        if stem[:5] == m.stem[:5]:
            meta = json.loads(m.read_text(encoding="utf-8"))
            return meta.get("title", stem.replace("_", " "))
    return stem.replace("_", " ")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--create-only", action="store_true", help="Only create Shorts, don't upload")
    p.add_argument("--upload-only", action="store_true", help="Only upload existing Shorts")
    p.add_argument("--limit", type=int, default=999, help="Max videos to process")
    args = p.parse_args()

    SHORTS_DIR.mkdir(parents=True, exist_ok=True)

    ready_videos = get_ready_videos()
    if not ready_videos:
        print("No rendered videos found. Run run_pipeline.py first.")
        return

    print(f"Found {len(ready_videos)} rendered videos.")

    # ── STEP 1: Create Shorts ───────────────────────────────────────────────
    if not args.upload_only:
        print(f"\nCreating vertical Shorts...")
        created = 0
        for i, video_path in enumerate(ready_videos[:args.limit]):
            title = get_title_for_video(video_path)
            short_stem = f"short_{video_path.stem[:50]}"
            short_path = SHORTS_DIR / f"{short_stem}.mp4"

            if short_path.exists() and short_path.stat().st_size > 50_000:
                print(f"  [{i+1}] Already exists: {short_path.name}")
                created += 1
                continue

            print(f"  [{i+1}/{min(len(ready_videos), args.limit)}] Creating: {title[:55]}")
            ok = create_short(video_path, title, short_path)
            if ok:
                size = short_path.stat().st_size / 1_048_576
                print(f"    OK — {size:.1f} MB")
                created += 1
            else:
                print(f"    FAILED")

        print(f"\nCreated {created} Shorts in {SHORTS_DIR}")

    # ── STEP 2: Upload Shorts ───────────────────────────────────────────────
    if not args.create_only:
        print(f"\nUploading Shorts to YouTube (PUBLIC)...")
        try:
            creds = load_credentials()
            service = build_service(creds)
            resp = service.channels().list(mine=True, part="snippet").execute()
            print(f"  Channel: {resp['items'][0]['snippet']['title']}\n")
        except Exception as e:
            print(f"ERROR: Credentials failed: {e}")
            return

        uploaded_titles = get_uploaded_titles()
        uploaded_count = 0

        short_files = sorted(SHORTS_DIR.glob("short_*.mp4"))
        for i, short_path in enumerate(short_files[:args.limit]):
            # Find matching title
            stem_no_prefix = short_path.stem.replace("short_", "")
            orig_video = next(
                (v for v in ready_videos if v.stem[:50] == stem_no_prefix[:50]),
                None
            )
            title = get_title_for_video(orig_video) if orig_video else stem_no_prefix.replace("_", " ")
            short_title = f"{title} #Shorts"

            if short_title in uploaded_titles or title in uploaded_titles:
                print(f"  [{i+1}] Already uploaded: {title[:50]}")
                continue

            print(f"  [{i+1}/{len(short_files)}] Uploading Short: {title[:50]}")
            try:
                result = upload_short(
                    service, short_path, short_title,
                    f"Quick breakdown: {title}",
                    ["personal finance", "money", "shorts", "financial tips"]
                )
                uploaded_count += 1
                print(f"    OK -> {result['url']}")
                time.sleep(8)
            except Exception as e:
                err = str(e)
                print(f"    FAILED: {err[:100]}")
                if "uploadLimitExceeded" in err or "quota" in err.lower():
                    print("  Daily limit reached.")
                    break
                time.sleep(3)

        print(f"\nUploaded {uploaded_count} Shorts.")


if __name__ == "__main__":
    main()

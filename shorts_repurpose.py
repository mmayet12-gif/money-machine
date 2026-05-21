#!/usr/bin/env python3
"""
Short-Form Repurposing — converts long-form videos into Shorts, TikToks, and Reels.

Features:
  - Auto-resize to 9:16 (1080x1920) with smart cropping
  - Clip selection: extracts most engaging segments (hook + key sections)
  - Caption adaptation for vertical format
  - Hook rewriting for short-form
  - Per-platform export settings (YouTube Shorts, TikTok, Reels)
  - Batch processing

Usage:
    python shorts_repurpose.py --input output\\videos\\01_xxx.mp4
    python shorts_repurpose.py --input output\\videos\\01_xxx.mp4 --platform tiktok
    python shorts_repurpose.py --batch output\\videos
    python shorts_repurpose.py --batch output\\videos --max-duration 30
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\money-machine")
METADATA_DIR = ROOT / "output" / "metadata"
SHORTS_DIR = ROOT / "output" / "shorts"
SCRIPTS_DIR = ROOT / "scripts"

# Platform presets
PLATFORMS = {
    "youtube_shorts": {
        "max_duration": 58,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "4M",
        "audio_bitrate": "128k",
        "suffix": "_short",
        "hashtag": "#Shorts",
    },
    "tiktok": {
        "max_duration": 60,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "5M",
        "audio_bitrate": "128k",
        "suffix": "_tiktok",
        "hashtag": "#fyp #finance",
    },
    "reels": {
        "max_duration": 60,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "4M",
        "audio_bitrate": "128k",
        "suffix": "_reel",
        "hashtag": "#reels #moneytips",
    },
}

DEFAULT_PLATFORM = "youtube_shorts"


def get_video_info(video_path: Path) -> dict:
    """Get video duration, resolution, etc via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(video_path),
        ],
        capture_output=True, text=True, timeout=30,
    )
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    width = height = 0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream["width"])
            height = int(stream["height"])
            break
    return {"duration": duration, "width": width, "height": height}


def find_metadata(video_path: Path) -> dict | None:
    stem = video_path.stem
    meta_path = METADATA_DIR / f"{stem}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    for c in sorted(METADATA_DIR.glob("*.json")):
        if stem[:5] == c.stem[:5]:
            return json.loads(c.read_text(encoding="utf-8"))
    return None


def find_script(video_path: Path) -> str | None:
    stem = video_path.stem
    for txt in sorted(SCRIPTS_DIR.glob("*.txt")):
        if stem[:5] == txt.stem[:5]:
            return txt.read_text(encoding="utf-8", errors="replace")
    return None


def select_clips(
    duration: float,
    script_text: str | None,
    max_duration: float,
    num_clips: int = 3,
) -> list[dict]:
    """
    Select the most engaging segments from a long-form video.

    Strategy:
      1. Hook: always take the first 5-8 seconds
      2. Key points: extract from sections marked with strong language
      3. Close: take the last call-to-action segment

    Each clip is a dict with 'start', 'end', 'label'.
    """
    clips = []

    if duration <= max_duration:
        return [{"start": 0, "end": min(duration, max_duration), "label": "full"}]

    # Hook — first 8 seconds
    hook_end = min(8.0, duration * 0.1)
    clips.append({"start": 0, "end": hook_end, "label": "hook"})

    remaining = max_duration - hook_end - 6.0  # Reserve 6s for close

    if script_text:
        # Find sections with engagement markers
        lines = script_text.splitlines()
        section_starts = []
        for i, line in enumerate(lines):
            if re.match(r"^\s*(?:#{1,3}|(?:\*\*))?\s*(?:Act|Hook|Context|Close)", line, re.IGNORECASE):
                section_starts.append(i)

        # Take middle sections proportionally
        if len(section_starts) >= 3:
            mid_sections = section_starts[1:-1]
            per_section = remaining / max(1, min(len(mid_sections), num_clips - 2))

            for j, sec_start_line in enumerate(mid_sections[:num_clips - 2]):
                frac = sec_start_line / max(1, len(lines))
                time_start = hook_end + frac * (duration - hook_end - 8)
                clip_end = min(time_start + per_section, duration - 6)
                if clip_end > time_start + 3:
                    clips.append({"start": time_start, "end": clip_end, "label": f"key_{j + 1}"})
        else:
            # No clear sections — take from the first third
            mid_start = hook_end + 2
            mid_end = min(mid_start + remaining, duration - 8)
            if mid_end > mid_start:
                clips.append({"start": mid_start, "end": mid_end, "label": "middle"})
    else:
        # No script — take proportional chunks
        mid_start = hook_end + 2
        mid_end = min(mid_start + remaining, duration - 8)
        if mid_end > mid_start:
            clips.append({"start": mid_start, "end": mid_end, "label": "middle"})

    # Close — last 6 seconds
    close_start = max(duration - 6, clips[-1]["end"] + 0.5 if clips else 0)
    clips.append({"start": close_start, "end": duration, "label": "close"})

    # Verify total fits in max_duration
    total = sum(c["end"] - c["start"] for c in clips)
    if total > max_duration:
        # Trim middle clips
        excess = total - max_duration
        for c in reversed(clips):
            if c["label"] not in ("hook", "close"):
                trim = min(excess, c["end"] - c["start"] - 3)
                if trim > 0:
                    c["end"] -= trim
                    excess -= trim
            if excess <= 0:
                break

    return clips


def rewrite_hook(title: str) -> str:
    """Rewrite a long-form title as a short-form hook."""
    title = title.strip()
    if len(title) <= 50:
        return title

    # Shorten by removing common filler
    title = re.sub(r"\s+in\s+\d{4}", "", title)
    title = re.sub(r"\s+That\s+Actually\s+Works?", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+You\s+Need\s+to\s+Know", "", title, flags=re.IGNORECASE)

    if len(title) > 50:
        title = title[:47] + "..."

    return title


def crop_to_vertical(
    input_path: Path,
    output_path: Path,
    clips: list[dict],
    platform: dict,
) -> None:
    """
    Use ffmpeg to crop horizontal video to vertical 9:16 with smart center crop,
    concatenating selected clips.
    """
    w = platform["width"]
    h = platform["height"]
    fps = platform["fps"]
    bitrate = platform["bitrate"]
    audio_br = platform["audio_bitrate"]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(clips) == 1 and clips[0]["label"] == "full":
        # Simple crop of the whole video
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-t", str(platform["max_duration"]),
            "-vf", (
                f"crop=in_h*{w}/{h}:in_h,"
                f"scale={w}:{h},"
                f"setsar=1"
            ),
            "-r", str(fps),
            "-c:v", "libx264",
            "-b:v", bitrate,
            "-c:a", "aac",
            "-b:a", audio_br,
            "-preset", "fast",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg crop failed: {result.stderr[-500:]}")
        return

    # Multiple clips — use ffmpeg concat filter
    filter_parts = []
    inputs = []
    for i, clip in enumerate(clips):
        inputs.extend(["-ss", f"{clip['start']:.2f}", "-t", f"{clip['end'] - clip['start']:.2f}", "-i", str(input_path)])
        filter_parts.append(
            f"[{i}:v]crop=in_h*{w}/{h}:in_h,scale={w}:{h},setsar=1,fps={fps}[v{i}];"
            f"[{i}:a]aresample=44100[a{i}];"
        )

    # Concat
    v_concat = "".join(f"[v{i}]" for i in range(len(clips)))
    a_concat = "".join(f"[a{i}]" for i in range(len(clips)))
    filter_parts.append(f"{v_concat}concat=n={len(clips)}:v=1:a=0[vout];")
    filter_parts.append(f"{a_concat}concat=n={len(clips)}:v=0:a=1[aout]")

    filter_complex = "".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-b:v", bitrate,
        "-c:a", "aac",
        "-b:a", audio_br,
        "-preset", "fast",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {result.stderr[-500:]}")


def process_video(
    video_path: Path,
    platform_name: str = DEFAULT_PLATFORM,
    max_duration: float | None = None,
) -> Path | None:
    """Process a single long-form video into a short-form clip."""
    platform = PLATFORMS[platform_name]
    max_dur = max_duration or platform["max_duration"]

    print(f"\n  Processing: {video_path.name}")
    print(f"  Platform:   {platform_name}")

    info = get_video_info(video_path)
    print(f"  Source:     {info['width']}x{info['height']}, {info['duration']:.1f}s")

    script_text = find_script(video_path)
    metadata = find_metadata(video_path)

    clips = select_clips(info["duration"], script_text, max_dur)
    total_clip_dur = sum(c["end"] - c["start"] for c in clips)
    print(f"  Clips:      {len(clips)} segments, {total_clip_dur:.1f}s total")
    for c in clips:
        print(f"              [{c['label']}] {c['start']:.1f}s - {c['end']:.1f}s")

    # Output filename
    stem = video_path.stem
    if metadata:
        short_title = rewrite_hook(metadata.get("title", stem))
    else:
        short_title = stem

    out_name = f"{stem}{platform['suffix']}.mp4"
    platform_dir = SHORTS_DIR / platform_name
    platform_dir.mkdir(parents=True, exist_ok=True)
    out_path = platform_dir / out_name

    t0 = time.time()
    crop_to_vertical(video_path, out_path, clips, platform)
    elapsed = time.time() - t0

    size_mb = out_path.stat().st_size / 1_048_576
    print(f"  Output:     {out_path}")
    print(f"  Size:       {size_mb:.1f} MB, rendered in {elapsed:.0f}s")

    # Write metadata sidecar
    short_meta = {
        "source_video": str(video_path),
        "platform": platform_name,
        "title": short_title,
        "hashtags": platform["hashtag"],
        "clips": clips,
        "duration": total_clip_dur,
        "created_at": datetime.now().isoformat(),
    }
    meta_out = out_path.with_suffix(".json")
    meta_out.write_text(json.dumps(short_meta, indent=2), encoding="utf-8")

    return out_path


def cmd_single(args) -> int:
    video_path = Path(args.input).resolve()
    if not video_path.exists():
        print(f"ERROR: File not found: {video_path}")
        return 1

    platforms = [args.platform] if args.platform else list(PLATFORMS.keys())

    for pname in platforms:
        try:
            process_video(video_path, pname, args.max_duration)
        except Exception as e:
            print(f"ERROR ({pname}): {e}")
            return 1

    return 0


def cmd_batch(args) -> int:
    video_dir = Path(args.batch).resolve()
    if not video_dir.exists():
        print(f"ERROR: Directory not found: {video_dir}")
        return 1

    mp4s = sorted(video_dir.glob("*.mp4"))
    if not mp4s:
        print(f"No .mp4 files in {video_dir}")
        return 0

    platforms = [args.platform] if args.platform else [DEFAULT_PLATFORM]

    print(f"Found {len(mp4s)} videos, repurposing for: {', '.join(platforms)}")
    successes = 0
    failures = 0

    for mp4 in mp4s:
        for pname in platforms:
            try:
                process_video(mp4, pname, args.max_duration)
                successes += 1
            except Exception as e:
                print(f"FAILED: {mp4.name} ({pname}): {e}")
                failures += 1

    print(f"\nDone: {successes} succeeded, {failures} failed")
    print(f"Shorts saved to: {SHORTS_DIR}")
    return 0 if failures == 0 else 2


def main() -> int:
    p = argparse.ArgumentParser(
        description="Convert long-form videos into YouTube Shorts, TikToks, and Reels",
    )
    p.add_argument("--input", metavar="VIDEO", help="Single video to repurpose")
    p.add_argument("--batch", metavar="DIR", help="Batch process all .mp4s in a directory")
    p.add_argument(
        "--platform",
        choices=list(PLATFORMS.keys()),
        help="Target platform (default: all platforms)",
    )
    p.add_argument(
        "--max-duration",
        type=float,
        help="Override max clip duration in seconds",
    )
    args = p.parse_args()

    if args.input:
        return cmd_single(args)
    if args.batch:
        return cmd_batch(args)

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

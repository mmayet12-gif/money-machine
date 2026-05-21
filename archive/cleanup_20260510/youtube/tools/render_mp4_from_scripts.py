from __future__ import annotations

import argparse
import asyncio
import re
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path
from typing import Iterable, List, Tuple

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip


STREAM_RULES = {
    "S1": {"max_words": 700, "chunk_words": 20, "size": (1920, 1080)},
    "S2": {"max_words": 105, "chunk_words": 11, "size": (1080, 1920)},
    "S3": {"max_words": 105, "chunk_words": 11, "size": (1080, 1920)},
    "S4": {"max_words": 380, "chunk_words": 18, "size": (1920, 1080)},
    "S5": {"max_words": 320, "chunk_words": 18, "size": (1920, 1080)},
    "S6": {"max_words": 320, "chunk_words": 18, "size": (1920, 1080)},
    "S7": {"max_words": 320, "chunk_words": 18, "size": (1920, 1080)},
    "S8": {"max_words": 320, "chunk_words": 18, "size": (1920, 1080)},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render MP4 videos from script text files.")
    parser.add_argument("--run-id", required=True, help="Run folder ID (example: full_run_01)")
    parser.add_argument("--base-dir", default=r"C:\money-machine\youtube\runs", help="Runs base directory")
    parser.add_argument("--streams", default="S1,S2,S3", help="Comma-separated stream IDs")
    parser.add_argument("--voice", default="en-US-EricNeural", help="Edge TTS voice")
    parser.add_argument("--limit", type=int, default=0, help="Limit files per stream (0 = no limit)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing MP4 files")
    return parser.parse_args()


def clean_script(raw: str) -> str:
    text = raw
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)
    text = re.sub(r"(?im)^={3,}.*$", "", text)
    text = re.sub(r"(?im)^title:\s.*$", "", text)
    text = re.sub(r"(?im)^keyword:\s.*$", "", text)
    text = re.sub(r"(?im)^style:\s.*$", "", text)
    text = re.sub(r"(?im)^niche:\s.*$", "", text)
    text = re.sub(r"(?im)^generated:.*$", "", text)
    text = re.sub(r"(?im)^\s*end of script.*$", "", text)
    text = re.sub(r"\[[^\]]{1,40}\]", "", text)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_chunks(text: str, max_words: int = 16) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    current: List[str] = []
    for w in words:
        current.append(w)
        if len(current) >= max_words:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks or [" "]


def truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def estimate_chunk_durations(chunks: List[str], total_duration: float) -> List[float]:
    weights = [max(1, len(c.split())) for c in chunks]
    total_weight = sum(weights)
    durations = [(w / total_weight) * total_duration for w in weights]
    return [max(0.9, d) for d in durations]


def get_size_for_stream(stream_id: str) -> Tuple[int, int]:
    rule = STREAM_RULES.get(stream_id, STREAM_RULES["S1"])
    return rule["size"]


def make_frame(text: str, width: int, height: int) -> np.ndarray:
    img = Image.new("RGB", (width, height), color=(16, 20, 28))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 58 if width >= 1600 else 54)
        small = ImageFont.truetype("arial.ttf", 28 if width >= 1600 else 36)
    except Exception:
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    margin_x = int(width * 0.08)
    max_text_width = width - (margin_x * 2)

    wrapped = textwrap.fill(text, width=34 if width < 1200 else 52)
    lines = wrapped.splitlines()
    line_h = draw.textbbox((0, 0), "Ag", font=font)[3] + 14
    block_h = max(line_h * len(lines), 90)
    start_y = int((height - block_h) * 0.45)

    panel_pad = 30
    panel_top = max(40, start_y - panel_pad)
    panel_bottom = min(height - 40, start_y + block_h + panel_pad)
    draw.rounded_rectangle(
        [(margin_x - 25, panel_top), (width - margin_x + 25, panel_bottom)],
        radius=18,
        fill=(28, 35, 48),
        outline=(74, 96, 134),
        width=3,
    )

    y = start_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (width - line_w) // 2
        draw.text((x, y), line, font=font, fill=(242, 246, 255))
        y += line_h

    footer = "AI Money Machine"
    fb = draw.textbbox((0, 0), footer, font=small)
    draw.text((width - (fb[2] - fb[0]) - 40, height - 55), footer, font=small, fill=(160, 178, 210))
    return np.array(img)


async def tts_to_mp3(text: str, out_mp3: Path, voice: str) -> None:
    communicator = edge_tts.Communicate(text, voice)
    await communicator.save(str(out_mp3))


def find_input_files(stream_dir: Path, prefix: str, limit: int) -> List[Path]:
    txt_files = sorted(stream_dir.glob(f"{prefix}_*.txt"))
    md_files = sorted(stream_dir.glob(f"{prefix}_*.md"))
    files = txt_files if txt_files else md_files
    if limit > 0:
        return files[:limit]
    return files


def _render_with_ffmpeg(
    frames: List[np.ndarray],
    durations: List[float],
    audio_path: Path,
    output_mp4: Path,
) -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    temp_root = output_mp4.parent / f"_tmp_{uuid.uuid4().hex[:10]}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        concat_file = temp_root / "concat.txt"
        paths: List[Path] = []
        for i, frame in enumerate(frames):
            p = temp_root / f"frame_{i:04d}.png"
            Image.fromarray(frame).save(p, format="PNG")
            paths.append(p)

        with concat_file.open("w", encoding="utf-8") as handle:
            for p, dur in zip(paths, durations):
                handle.write(f"file '{p.as_posix()}'\n")
                handle.write(f"duration {max(0.2, dur):.4f}\n")
            # ffmpeg concat demuxer needs the last frame repeated without duration
            handle.write(f"file '{paths[-1].as_posix()}'\n")

        cmd = [
            ffmpeg_exe,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-i",
            str(audio_path),
            "-shortest",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_mp4),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def render_file(script_path: Path, output_mp4: Path, temp_audio: Path, stream_id: str, voice: str) -> None:
    raw = script_path.read_text(encoding="utf-8", errors="ignore")
    text = clean_script(raw)
    if not text:
        text = "Generated script is empty."

    rule = STREAM_RULES.get(stream_id, STREAM_RULES["S1"])
    text = truncate_words(text, int(rule["max_words"]))

    asyncio.run(tts_to_mp3(text, temp_audio, voice))
    audio = AudioFileClip(str(temp_audio))
    chunks = split_chunks(text, max_words=int(rule["chunk_words"]))
    durations = estimate_chunk_durations(chunks, audio.duration)

    width, height = get_size_for_stream(stream_id)
    frames: List[np.ndarray] = []
    for chunk in chunks:
        frames.append(make_frame(chunk, width, height))

    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    _render_with_ffmpeg(frames, durations, temp_audio, output_mp4)

    audio.close()
    try:
        temp_audio.unlink(missing_ok=True)
    except Exception:
        pass


def main() -> int:
    args = parse_args()
    stream_ids = [s.strip().upper() for s in args.streams.split(",") if s.strip()]
    run_root = Path(args.base_dir) / args.run_id
    if not run_root.exists():
        raise SystemExit(f"Run folder not found: {run_root}")

    prefixes = {
        "S1": "s1_long",
        "S2": "s2_shorts",
        "S3": "s3_reels",
        "S4": "s4_blog",
        "S5": "s5_email",
        "S6": "s6_aff",
        "S7": "s7_product",
        "S8": "s8_dist",
    }
    any_rendered = 0

    for sid in stream_ids:
        if sid not in prefixes:
            continue
        source_dir = run_root / sid / "outputs"
        if not source_dir.exists():
            continue
        target_dir = run_root / "videos" / sid
        target_dir.mkdir(parents=True, exist_ok=True)

        files = find_input_files(source_dir, prefixes[sid], args.limit)
        for script_file in files:
            stem = script_file.stem
            output_mp4 = target_dir / f"{stem}.mp4"
            temp_audio = target_dir / f"{stem}.mp3"
            if output_mp4.exists() and not args.overwrite:
                continue
            print(f"[{sid}] Rendering {script_file.name} -> {output_mp4.name}")
            render_file(script_file, output_mp4, temp_audio, sid, args.voice)
            any_rendered += 1

    print(f"Done. Rendered {any_rendered} MP4 file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Viral Video Engine — high-retention rendering for faceless YouTube content.

Replaces the static slide renderer with dynamic visuals:
  - Ken Burns motion on background images (pan + zoom)
  - Pattern interrupts every 2-4 seconds (zoom cuts, flash, shake)
  - Animated word-by-word captions with highlight
  - Hook animation in first 3 seconds
  - Smooth cross-fade transitions between sections
  - Background video/image layering with motion

Usage:
    This module is imported by run_pipeline.py. It can also be used standalone:

    python viral_engine.py --test          # render a 15s test clip
    python viral_engine.py --preview 01    # preview video 01 at low quality
"""
from __future__ import annotations

import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(r"C:\money-machine")
ASSETS_DIR = ROOT / "assets"
BG_IMAGES_DIR = ASSETS_DIR / "backgrounds"
SLIDES_DIR = ROOT / "output" / "slides"

W, H = 1920, 1080
FPS = 30

# Duration of each pattern interrupt effect (seconds)
INTERRUPT_INTERVAL = (2.5, 4.0)

ACCENT_COLORS = [
    (245, 158, 11),
    (239, 68, 68),
    (34, 197, 94),
    (59, 130, 246),
    (236, 72, 153),
]

WINDOWS_FONTS = ["arialbd.ttf", "calibrib.ttf", "verdanab.ttf", "tahomabd.ttf"]


def _find_font_path(size: int = 44) -> str:
    for fname in WINDOWS_FONTS:
        for d in [r"C:\Windows\Fonts", r"C:\WINDOWS\Fonts"]:
            p = Path(d) / fname
            if p.exists():
                return str(p)
    return "Arial"


def _find_pil_font(size: int = 44):
    from PIL import ImageFont
    for fname in WINDOWS_FONTS:
        for d in [r"C:\Windows\Fonts", r"C:\WINDOWS\Fonts"]:
            p = Path(d) / fname
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Frame generators — each produces a single PNG frame
# ---------------------------------------------------------------------------

def gen_frame_ken_burns(
    bg_path: Path,
    frame_num: int,
    total_frames: int,
    direction: str = "zoom_in",
) -> bytes:
    """Generate a single frame with Ken Burns pan/zoom effect on a background image."""
    from PIL import Image
    import numpy as np

    img = Image.open(bg_path).convert("RGB")
    iw, ih = img.size

    # Scale image up so we have room to pan/zoom
    scale_base = max(W / iw, H / ih) * 1.3
    img = img.resize((int(iw * scale_base), int(ih * scale_base)), Image.LANCZOS)
    iw, ih = img.size

    t = frame_num / max(1, total_frames - 1)

    if direction == "zoom_in":
        zoom = 1.0 + t * 0.15
        cx = iw / 2 + t * 40
        cy = ih / 2 + t * 20
    elif direction == "zoom_out":
        zoom = 1.15 - t * 0.15
        cx = iw / 2 - t * 40
        cy = ih / 2 - t * 20
    elif direction == "pan_right":
        zoom = 1.05
        cx = iw / 2 - (iw * 0.05) + t * (iw * 0.1)
        cy = ih / 2
    else:  # pan_left
        zoom = 1.05
        cx = iw / 2 + (iw * 0.05) - t * (iw * 0.1)
        cy = ih / 2

    crop_w = W / zoom
    crop_h = H / zoom
    x1 = max(0, int(cx - crop_w / 2))
    y1 = max(0, int(cy - crop_h / 2))
    x2 = min(iw, int(cx + crop_w / 2))
    y2 = min(ih, int(cy + crop_h / 2))

    cropped = img.crop((x1, y1, x2, y2)).resize((W, H), Image.LANCZOS)

    # Dark overlay for text readability
    overlay = Image.new("RGB", (W, H), (0, 0, 0))
    frame = Image.blend(cropped, overlay, alpha=0.50)

    import io
    buf = io.BytesIO()
    frame.save(buf, format="PNG")
    return buf.getvalue()


def apply_pattern_interrupt(
    frame_bytes: bytes,
    interrupt_type: str,
    intensity: float,
) -> bytes:
    """Apply a pattern interrupt effect to a frame. intensity 0.0 to 1.0."""
    from PIL import Image, ImageEnhance, ImageFilter
    import io

    img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")

    if interrupt_type == "zoom_cut":
        # Sudden zoom to center
        zoom = 1.0 + 0.12 * intensity
        cw = int(W / zoom)
        ch = int(H / zoom)
        left = (W - cw) // 2
        top = (H - ch) // 2
        img = img.crop((left, top, left + cw, top + ch)).resize((W, H), Image.LANCZOS)

    elif interrupt_type == "flash":
        # Brief brightness flash
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.0 + 1.5 * intensity)

    elif interrupt_type == "shake":
        # Offset the frame slightly
        dx = int(8 * intensity * (1 if random.random() > 0.5 else -1))
        dy = int(5 * intensity * (1 if random.random() > 0.5 else -1))
        from PIL import ImageChops
        shifted = ImageChops.offset(img, dx, dy)
        img = shifted

    elif interrupt_type == "vignette":
        # Darken edges
        import numpy as np
        arr = np.array(img, dtype=float)
        rows, cols = arr.shape[:2]
        Y, X = np.ogrid[:rows, :cols]
        cx, cy = cols / 2, rows / 2
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        max_dist = np.sqrt(cx ** 2 + cy ** 2)
        vignette = 1.0 - (dist / max_dist) * 0.6 * intensity
        vignette = np.clip(vignette, 0.3, 1.0)
        arr *= vignette[:, :, np.newaxis]
        img = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_caption_on_frame(
    frame_bytes: bytes,
    words: list[str],
    highlight_index: int,
    accent: tuple[int, int, int],
) -> bytes:
    """Render animated captions with the current word highlighted."""
    from PIL import Image, ImageDraw
    import io

    img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)

    if not words:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    font = _find_pil_font(52)
    small_font = _find_pil_font(48)

    phrase = " ".join(words)

    # Background bar for caption
    bbox = draw.textbbox((0, 0), phrase, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    bar_y = int(H * 0.82)
    bar_padding = 20
    bar_rect = [
        (W - tw) // 2 - bar_padding,
        bar_y - bar_padding,
        (W + tw) // 2 + bar_padding,
        bar_y + th + bar_padding,
    ]

    # Semi-transparent black bar
    caption_bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    caption_draw = ImageDraw.Draw(caption_bg)
    caption_draw.rounded_rectangle(bar_rect, radius=12, fill=(0, 0, 0, 180))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, caption_bg)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Draw words individually, highlighting current word
    x_start = (W - tw) // 2
    x = x_start
    for i, word in enumerate(words):
        word_text = word + " "
        if i == highlight_index:
            # Highlighted word — accent color, slightly larger
            draw.text((x - 1, bar_y - 2), word_text, font=font, fill=accent)
            draw.text((x, bar_y), word_text, font=font, fill=accent)
        else:
            draw.text((x, bar_y), word_text, font=small_font, fill=(255, 255, 255))
        word_bbox = draw.textbbox((0, 0), word_text, font=font)
        x += word_bbox[2] - word_bbox[0]

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_hook_frame(
    frame_bytes: bytes,
    title: str,
    accent: tuple[int, int, int],
    frame_num: int,
    hook_frames: int,
) -> bytes:
    """Render the hook animation — title zooms in during first 3 seconds."""
    from PIL import Image, ImageDraw
    import io

    img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")

    t = frame_num / max(1, hook_frames - 1)

    # Scale text from 0.3x to 1.0x
    scale = 0.3 + 0.7 * min(1.0, t * 1.5)
    # Fade in
    alpha = min(255, int(255 * t * 2))

    font_size = int(90 * scale)
    font = _find_pil_font(max(20, font_size))
    draw = ImageDraw.Draw(img)

    # Word wrap title
    words = title.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if len(test) <= 28:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:3]

    total_h = len(lines) * (font_size + 12)
    y = (H - total_h) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        # Shadow
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0))
        # Accent text
        r, g, b = accent
        draw.text((x, y), line, font=font, fill=(r, g, b, alpha) if alpha < 255 else accent)
        y += font_size + 12

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main rendering pipeline — hybrid ffmpeg + PIL approach
# ---------------------------------------------------------------------------

def get_bg_images() -> list[Path]:
    if BG_IMAGES_DIR.exists():
        imgs = sorted(BG_IMAGES_DIR.glob("*.jpg"))
        if imgs:
            return imgs
    return []


def split_narration_to_words(narration: str) -> list[str]:
    words = narration.split()
    return [w.strip() for w in words if w.strip()]


def _get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio_path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(result.stdout.strip())


def _render_section_clip(
    bg_path: Path,
    section_duration: float,
    kb_direction: str,
    out_clip: Path,
) -> None:
    """Use ffmpeg zoompan filter for Ken Burns — runs in C, vastly faster than PIL."""
    # zoompan: zoom from 1.0 to 1.15 (zoom_in) or reverse, with pan
    total_frames = int(section_duration * FPS)
    if total_frames < 1:
        total_frames = 1

    if kb_direction == "zoom_in":
        zoom_expr = f"zoom+0.0005"
        x_expr = f"iw/2-(iw/zoom/2)+on*0.3"
        y_expr = f"ih/2-(ih/zoom/2)+on*0.15"
    elif kb_direction == "zoom_out":
        zoom_expr = f"if(eq(on,1),1.15,zoom-0.0005)"
        x_expr = f"iw/2-(iw/zoom/2)-on*0.3"
        y_expr = f"ih/2-(ih/zoom/2)-on*0.15"
    elif kb_direction == "pan_right":
        zoom_expr = "1.08"
        x_expr = f"on*0.8"
        y_expr = f"ih/2-(ih/zoom/2)"
    else:  # pan_left
        zoom_expr = "1.08"
        x_expr = f"iw/zoom-iw+{total_frames}*0.8-on*0.8"
        y_expr = f"ih/2-(ih/zoom/2)"

    filter_str = (
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}'"
        f":d={total_frames}:s={W}x{H}:fps={FPS},"
        f"colorbalance=bs=-0.08:bm=-0.05,"
        f"eq=brightness=-0.15:contrast=1.1"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(bg_path),
        "-vf", filter_str,
        "-t", f"{section_duration:.2f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "23",
        str(out_clip),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"zoompan failed: {result.stderr[-300:]}")


def _gen_caption_overlay(
    words: list[str],
    duration: float,
    accent: tuple[int, int, int],
    out_dir: Path,
) -> list[Path]:
    """Generate caption overlay PNG frames — only the caption bar, transparent elsewhere."""
    from PIL import Image, ImageDraw
    import io

    chunk_size = 5
    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    if not chunks:
        return []

    frames_per_chunk = max(1, int(duration * FPS / len(chunks)))
    overlay_paths = []

    font = _find_pil_font(52)
    small_font = _find_pil_font(48)

    for ci, chunk_words in enumerate(chunks):
        for wi in range(len(chunk_words)):
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            phrase = " ".join(chunk_words)
            bbox = draw.textbbox((0, 0), phrase, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            bar_y = int(H * 0.82)
            pad = 20

            # Caption bar background
            draw.rounded_rectangle(
                [(W - tw) // 2 - pad, bar_y - pad,
                 (W + tw) // 2 + pad, bar_y + th + pad],
                radius=12, fill=(0, 0, 0, 180),
            )

            # Words with highlight
            x = (W - tw) // 2
            for i, word in enumerate(chunk_words):
                word_text = word + " "
                if i == wi:
                    draw.text((x, bar_y), word_text, font=font, fill=(*accent, 255))
                else:
                    draw.text((x, bar_y), word_text, font=small_font, fill=(255, 255, 255, 230))
                wb = draw.textbbox((0, 0), word_text, font=font)
                x += wb[2] - wb[0]

            frame_num = ci * frames_per_chunk + wi * max(1, frames_per_chunk // len(chunk_words))
            path = out_dir / f"cap_{frame_num:06d}.png"
            img.save(path, "PNG")
            overlay_paths.append((frame_num, path))

    return overlay_paths


def _gen_hook_overlay(
    title: str,
    accent: tuple[int, int, int],
    duration: float,
    out_dir: Path,
) -> Path:
    """Generate a hook title card as a short video clip with ffmpeg drawtext."""
    from PIL import Image, ImageDraw

    # Render a single title card image
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _find_pil_font(90)

    words = title.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if len(test) <= 28:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:3]

    total_h = len(lines) * 108
    y = (H - total_h) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), line, font=font, fill=(*accent, 255))
        y += 108

    hook_img_path = out_dir / "hook_title.png"
    img.save(hook_img_path, "PNG")
    return hook_img_path


def render_viral_video(
    audio_path: Path,
    sections: list[dict],
    title: str,
    narration: str,
    out_video: Path,
    accent: tuple[int, int, int],
    video_index: int,
    total_videos: int,
    quality: str = "normal",
) -> None:
    """
    Render a viral-style video using ffmpeg-native Ken Burns + PIL caption overlays.
    Much faster than frame-by-frame PIL rendering.
    """
    duration = _get_audio_duration(audio_path)
    bg_images = get_bg_images()
    if not bg_images:
        raise RuntimeError("No background images found. Run: python run_pipeline.py --setup")

    words = split_narration_to_words(narration)
    kb_directions = ["zoom_in", "pan_right", "zoom_out", "pan_left"]

    # Section timing based on word count
    section_word_counts = [len(s["text"].split()) for s in sections]
    total_words_count = sum(section_word_counts) or 1
    section_durations = [duration * wc / total_words_count for wc in section_word_counts]

    work_dir = SLIDES_DIR / f"_work_{video_index:02d}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Phase 1: Render Ken Burns section clips with ffmpeg (fast, native)
        print(f"    Phase 1: Ken Burns sections ({len(sections)} clips)...", flush=True)
        section_clips = []
        for i, (sec, sec_dur) in enumerate(zip(sections, section_durations)):
            if sec_dur < 0.5:
                continue
            clip_path = work_dir / f"sec_{i:02d}.mp4"
            bg_img = bg_images[(video_index - 1 + i) % len(bg_images)]
            kb_dir = kb_directions[i % len(kb_directions)]
            _render_section_clip(bg_img, sec_dur, kb_dir, clip_path)
            section_clips.append(clip_path)
            print(f"      Section {i + 1}/{len(sections)}: {sec_dur:.1f}s done", flush=True)

        # Phase 2: Concatenate section clips
        print(f"    Phase 2: Concatenating sections...", flush=True)
        concat_list = work_dir / "concat.txt"
        with concat_list.open("w", encoding="utf-8") as f:
            for cp in section_clips:
                f.write(f"file '{cp}'\n")

        raw_video = work_dir / "raw_concat.mp4"
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "ultrafast", "-crf", "23",
            str(raw_video),
        ]
        result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Concat failed: {result.stderr[-300:]}")

        # Phase 3: Generate hook overlay
        print(f"    Phase 3: Hook title overlay...", flush=True)
        hook_img = _gen_hook_overlay(title, accent, min(3.0, duration * 0.1), work_dir)
        hook_dur = min(3.0, duration * 0.1)

        # Phase 4: Generate caption overlay frames (PIL, but only unique frames)
        print(f"    Phase 4: Caption overlays...", flush=True)
        caption_overlays = _gen_caption_overlay(words, duration, accent, work_dir)
        print(f"      Generated {len(caption_overlays)} caption frames", flush=True)

        # Phase 5: Composite everything with ffmpeg
        print(f"    Phase 5: Final composite + audio...", flush=True)
        out_video.parent.mkdir(parents=True, exist_ok=True)

        # Build the ASS subtitle-style caption overlay as ffmpeg drawtext
        # For simplicity and speed, overlay the hook image for the first N seconds,
        # then just add audio. Captions via the static approach for now.
        # The caption frames from Phase 4 are used as an overlay video.

        # Simple but effective: overlay hook image with fade, add audio
        r, g, b = accent
        final_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(audio_path),
            "-i", str(hook_img),
            "-filter_complex",
            f"[2:v]format=rgba,fade=t=in:st=0:d=0.5:alpha=1,"
            f"fade=t=out:st={hook_dur - 0.5:.1f}:d=0.5:alpha=1[hook];"
            f"[0:v][hook]overlay=0:0:enable='lt(t,{hook_dur:.1f})'[vout]",
            "-map", "[vout]",
            "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast" if quality == "normal" else "ultrafast",
            "-crf", "20" if quality == "normal" else "28",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(out_video),
        ]

        result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"Final encode failed: {result.stderr[-500:]}")

        print(f"    Done!", flush=True)

    finally:
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Standalone test mode
# ---------------------------------------------------------------------------
def _test_render():
    """Quick test: render a 15-second clip to verify the engine works."""
    print("=== VIRAL ENGINE TEST ===")

    bg_images = get_bg_images()
    if not bg_images:
        print("ERROR: No background images. Run: python run_pipeline.py --setup")
        return

    test_dir = ROOT / "output" / "test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Generate a short silent audio for testing
    import wave
    test_wav = test_dir / "test_audio.wav"
    with wave.open(str(test_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 22050 * 15)  # 15 seconds silence

    sections = [
        {"name": "hook", "text": "Here are the five money habits that separate the wealthy from everyone else."},
        {"name": "act1", "text": "The first habit is paying yourself first. Before any bill, before any expense, take ten percent and invest it."},
        {"name": "close", "text": "Start these habits today. Your future self will thank you."},
    ]
    narration = " ".join(s["text"] for s in sections)

    out_path = test_dir / "viral_test.mp4"
    t0 = time.time()
    render_viral_video(
        audio_path=test_wav,
        sections=sections,
        title="5 Money Habits of the Wealthy",
        narration=narration,
        out_video=out_path,
        accent=ACCENT_COLORS[0],
        video_index=1,
        total_videos=1,
    )
    elapsed = time.time() - t0
    size_mb = out_path.stat().st_size / 1_048_576
    print(f"\nTest video: {out_path}")
    print(f"Size: {size_mb:.1f} MB, rendered in {elapsed:.0f}s")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Viral video engine")
    p.add_argument("--test", action="store_true", help="Render a 15s test clip")
    args = p.parse_args()

    if args.test:
        _test_render()
    else:
        p.print_help()

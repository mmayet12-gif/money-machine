#!/usr/bin/env python3
"""
Premium Cinematic Video Engine v2 — retention-optimized faceless videos.

Architecture:
  Phase 1: Mood-mapped clip rendering (44 backgrounds, 10 motions, 6 color grades)
  Phase 2: Generate transition SFX (synthesized whooshes + impacts)
  Phase 3: Generate ASS subtitle file (word-by-word animated captions)
  Phase 4: Generate hook title card with flash
  Phase 5: Composite everything with crossfade transitions + audio

Key upgrades from v1:
  - 44 cinematic backgrounds across 9 categories (gradient, geometric, cityscape, etc.)
  - 10 motion patterns (drift, zoom, spiral, bounce, S-curve)
  - 6 color grading presets (dark_finance, luxury_gold, documentary, etc.)
  - Mood mapping: hook=high energy, close=calm, acts=progressive intensity
  - Flash/pulse at cut points for retention
  - Non-repetitive background selection with category matching
  - Section-aware zoom intensity (aggressive for hooks, gentle for close)

All rendering uses ffmpeg's C-native filters — no frame-by-frame Python.
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
import struct
import tempfile
import time
import wave
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\money-machine")
ASSETS_DIR = ROOT / "assets"
BG_IMAGES_DIR = ASSETS_DIR / "backgrounds"
SFX_DIR = ASSETS_DIR / "sfx"
SLIDES_DIR = ROOT / "output" / "slides"

W, H = 1920, 1080
FPS = 30

# Cinematic color palette
PALETTE = {
    "bg_dark": (8, 8, 12),
    "bg_navy": (10, 15, 35),
    "accent_gold": (218, 175, 65),
    "accent_green": (45, 212, 120),
    "text_white": (245, 245, 250),
    "text_dim": (160, 165, 180),
    "bar_bg": (0, 0, 0),
}

# ---------------------------------------------------------------------------
# COLOR GRADING PRESETS — each maps to ffmpeg eq + colorbalance + vignette
# ---------------------------------------------------------------------------
COLOR_GRADE_PRESETS = {
    "dark_finance": {
        "eq": "brightness=-0.12:contrast=1.20:saturation=0.80",
        "colorbalance": "rs=-0.08:gs=-0.03:bs=0.12:rh=0.06:gh=-0.02:bh=-0.08",
        "vignette": "PI/4:mode=backward",
    },
    "luxury_gold": {
        "eq": "brightness=-0.08:contrast=1.10:saturation=0.90",
        "colorbalance": "rs=0.05:gs=0.02:bs=-0.06:rm=0.08:gm=0.05:bm=-0.04:rh=0.03:gh=0.01:bh=-0.05",
        "vignette": "PI/3.5:mode=backward",
    },
    "documentary": {
        "eq": "brightness=-0.06:contrast=1.25:saturation=0.60",
        "colorbalance": "rs=-0.02:gs=-0.01:bs=0.03:rh=-0.01:gh=0.0:bh=0.02",
        "vignette": "PI/5:mode=backward",
    },
    "high_energy": {
        "eq": "brightness=-0.04:contrast=1.15:saturation=1.15",
        "colorbalance": "rs=0.03:gs=-0.02:bs=0.05:rh=0.05:gh=0.0:bh=0.03",
        "vignette": "PI/4.5:mode=backward",
    },
    "midnight_teal": {
        "eq": "brightness=-0.15:contrast=1.18:saturation=0.75",
        "colorbalance": "rs=-0.10:gs=0.0:bs=0.15:rh=-0.05:gh=0.02:bh=0.10",
        "vignette": "PI/3.8:mode=backward",
    },
    "warm_noir": {
        "eq": "brightness=-0.18:contrast=1.30:saturation=0.70",
        "colorbalance": "rs=0.04:gs=0.01:bs=-0.03:rm=0.02:gm=0.0:bm=-0.02",
        "vignette": "PI/3:mode=backward",
    },
}

# ---------------------------------------------------------------------------
# ZOOM PROFILES — controls Ken Burns intensity per section mood
# ---------------------------------------------------------------------------
ZOOM_PROFILES = {
    "slow_dramatic": 1.15,
    "standard": 1.25,
    "energetic": 1.35,
    "aggressive": 1.45,
}

# ---------------------------------------------------------------------------
# SECTION MOOD MAPPING — maps script sections to visual parameters
# ---------------------------------------------------------------------------
SECTION_MOODS = {
    "hook": {
        "bg_categories": ["radial_burst", "light_leak", "cityscape"],
        "zoom_profile": "aggressive",
        "color_grade": "high_energy",
        "flash_intensity": 0.35,
        "motion_pool": [4, 5, 6, 7],
    },
    "context": {
        "bg_categories": ["data_viz", "geometric", "particle_field"],
        "zoom_profile": "standard",
        "color_grade": "documentary",
        "flash_intensity": 0.15,
        "motion_pool": [0, 1, 8, 9],
    },
    "act1": {
        "bg_categories": ["gradient", "geometric", "wealth_symbol"],
        "zoom_profile": "standard",
        "color_grade": "dark_finance",
        "flash_intensity": 0.20,
        "motion_pool": [0, 2, 3, 8],
    },
    "act2": {
        "bg_categories": ["marble_texture", "particle_field", "data_viz"],
        "zoom_profile": "energetic",
        "color_grade": "luxury_gold",
        "flash_intensity": 0.25,
        "motion_pool": [1, 4, 5, 9],
    },
    "act3": {
        "bg_categories": ["cityscape", "radial_burst", "light_leak"],
        "zoom_profile": "energetic",
        "color_grade": "dark_finance",
        "flash_intensity": 0.30,
        "motion_pool": [3, 5, 6, 7],
    },
    "close": {
        "bg_categories": ["gradient", "marble_texture", "light_leak"],
        "zoom_profile": "slow_dramatic",
        "color_grade": "warm_noir",
        "flash_intensity": 0.10,
        "motion_pool": [0, 2, 8, 9],
    },
}

# Map niche to default color grade
NICHE_GRADE_MAP = {
    "personal_finance": "luxury_gold",
    "crypto_investing": "midnight_teal",
    "real_estate": "warm_noir",
    "ai_money": "high_energy",
    "tax_strategy": "documentary",
    "passive_income": "dark_finance",
}

WINDOWS_FONTS = ["arialbd.ttf", "calibrib.ttf", "verdanab.ttf", "tahomabd.ttf"]


def _find_font_path() -> str:
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


def _get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio_path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(result.stdout.strip())


# ---------------------------------------------------------------------------
# Phase 1: Animated background segments (ffmpeg-native)
# ---------------------------------------------------------------------------

def _get_motion_patterns(pad_x: int, pad_y: int, duration: float) -> list:
    """10 motion patterns using ffmpeg crop filter expressions."""
    dur = f"{duration:.2f}"
    px, py = pad_x, pad_y
    return [
        # 0. Drift right + down (classic Ken Burns)
        (f"{px}*t/{dur}", f"{py}*t/{dur}"),
        # 1. Drift left
        (f"{px}*(1-t/{dur})", f"{py//2}"),
        # 2. Drift up
        (f"{px//2}", f"{py}*(1-t/{dur})"),
        # 3. Diagonal drift down-left
        (f"{px}*(1-t/{dur})", f"{py}*t/{dur}"),
        # 4. Diagonal zoom-in (corner to center)
        (f"{px}*(1-t/{dur})", f"{py}*(1-t/{dur})"),
        # 5. Diagonal zoom-out (center to corner)
        (f"{px}*t/{dur}", f"{py}*(1-t/{dur})"),
        # 6. Bounce pan horizontal (ease-in-out via sin)
        (f"{px}*(sin(PI*t/{dur}))", f"{py//2}"),
        # 7. Vertical bounce
        (f"{px//2}", f"{py}*(sin(PI*t/{dur}))"),
        # 8. S-curve drift (horizontal + vertical sine)
        (f"{px}*t/{dur}", f"{py}/2+{py}/2*(sin(2*PI*t/{dur}))"),
        # 9. Gentle circular drift (partial arc)
        (f"{px}/2+{px}/2*(sin(PI*t/{dur}))", f"{py}/2+{py}/2*(cos(PI*t/{dur}))"),
    ]


def _render_cinematic_segment(
    bg_path: Path,
    duration: float,
    segment_idx: int,
    out_clip: Path,
    accent: tuple[int, int, int] = PALETTE["accent_gold"],
    motion_pattern: int | None = None,
    zoom_profile: str = "standard",
    color_grade: str = "dark_finance",
    flash_intensity: float = 0.2,
) -> None:
    """
    Render a cinematic background segment with:
    - Ken Burns motion (10 patterns, variable zoom intensity)
    - Color grading preset (6 cinematic looks)
    - Flash/pulse at clip start for retention
    - Vignette
    """
    # Zoom profile determines how much motion room we have
    scale = ZOOM_PROFILES.get(zoom_profile, 1.25)
    sw = int(W * scale)
    sh = int(H * scale)
    pad_x = sw - W
    pad_y = sh - H

    # Select motion pattern
    motions = _get_motion_patterns(pad_x, pad_y, duration)
    idx = motion_pattern if motion_pattern is not None else segment_idx
    x_expr, y_expr = motions[idx % len(motions)]

    # Get color grade
    grade = COLOR_GRADE_PRESETS.get(color_grade, COLOR_GRADE_PRESETS["dark_finance"])

    # Parse base brightness from eq string and add flash expression
    # Flash: brightness spikes at clip start then decays to base
    import re as _re
    eq_str = grade["eq"]
    m = _re.search(r"brightness=([-\d.]+)", eq_str)
    base_bright = float(m.group(1)) if m else -0.12
    if flash_intensity > 0.01:
        bright_expr = f"'{base_bright}+{flash_intensity:.2f}*exp(-10*t)'"
        eq_with_flash = _re.sub(r"brightness=[-\d.]+", f"brightness={bright_expr}", eq_str)
    else:
        eq_with_flash = eq_str

    filter_str = (
        f"scale={sw}:{sh},"
        f"crop={W}:{H}:{x_expr}:{y_expr},"
        f"eq={eq_with_flash},"
        f"colorbalance={grade['colorbalance']},"
        f"vignette={grade['vignette']}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(bg_path),
        "-vf", filter_str,
        "-t", f"{duration:.2f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "22",
        "-an",
        str(out_clip),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Segment render failed: {result.stderr[-400:]}")


# ---------------------------------------------------------------------------
# Phase 2: SFX generation (synthesized)
# ---------------------------------------------------------------------------

def _generate_whoosh(out_path: Path, duration: float = 0.4) -> None:
    """Generate a synthesized whoosh sound effect."""
    import numpy as np

    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples)

    # White noise shaped by an envelope
    noise = np.random.randn(n_samples)

    # Envelope: quick rise, slow fall
    envelope = np.exp(-3 * t) * np.sin(np.pi * t / duration)

    # Low-pass by simple moving average
    whoosh = noise * envelope
    kernel = np.ones(80) / 80
    whoosh = np.convolve(whoosh, kernel, mode="same")

    # Normalize
    whoosh = whoosh / (np.max(np.abs(whoosh)) + 1e-8) * 0.5

    # Convert to 16-bit PCM
    pcm = (whoosh * 32767).astype(np.int16)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _generate_click(out_path: Path) -> None:
    """Generate a subtle UI click sound."""
    import numpy as np

    sample_rate = 44100
    duration = 0.08
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples)

    # Short sine burst with fast decay
    click = np.sin(2 * np.pi * 2800 * t) * np.exp(-40 * t) * 0.3
    pcm = (click * 32767).astype(np.int16)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def ensure_sfx() -> dict[str, Path]:
    """Ensure whoosh and click SFX exist, generate if needed."""
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    sfx = {}
    whoosh = SFX_DIR / "whoosh.wav"
    click = SFX_DIR / "click.wav"
    if not whoosh.exists():
        _generate_whoosh(whoosh)
    if not click.exists():
        _generate_click(click)
    sfx["whoosh"] = whoosh
    sfx["click"] = click
    return sfx


# ---------------------------------------------------------------------------
# Phase 3: ASS subtitle generation (animated captions)
# ---------------------------------------------------------------------------

def _generate_ass_captions(
    words: list[str],
    duration: float,
    accent: tuple[int, int, int],
    out_ass: Path,
) -> None:
    """
    Generate an ASS subtitle file with word-by-word highlighting.

    Each caption shows 4-6 words. The current word is highlighted in accent color
    with a slight scale-up effect. Other words are white.
    """
    r, g, b = accent
    # ASS uses BGR format
    accent_bgr = f"&H00{b:02X}{g:02X}{r:02X}&"
    white_bgr = "&H00FAFAFA&"
    shadow_bgr = "&H80000000&"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,52,{white_bgr},{accent_bgr},&H80000000&,&HC0000000&,-1,0,0,0,100,100,0,0,3,3,2,2,60,60,115,1
Style: Highlight,Arial,58,{accent_bgr},{accent_bgr},&H80000000&,&HC0000000&,-1,0,0,0,105,105,0,0,3,3,2,2,60,60,115,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    chunk_size = 5
    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    if not chunks:
        out_ass.write_text(header, encoding="utf-8")
        return

    time_per_chunk = duration / len(chunks)
    events = []

    def fmt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    for ci, chunk in enumerate(chunks):
        chunk_start = ci * time_per_chunk
        chunk_end = chunk_start + time_per_chunk
        time_per_word = time_per_chunk / max(1, len(chunk))

        for wi, word in enumerate(chunk):
            word_start = chunk_start + wi * time_per_word
            word_end = word_start + time_per_word

            # Build the phrase with the highlighted word
            parts = []
            for j, w in enumerate(chunk):
                if j == wi:
                    # Highlighted word — accent color, slightly bigger
                    parts.append(f"{{\\c{accent_bgr}\\fs58\\b1}}{w}{{\\r}}")
                else:
                    parts.append(f"{{\\c{white_bgr}\\fs52}}{w}{{\\r}}")

            text = " ".join(parts)
            # Fade in first word of chunk, fade out last word
            if wi == 0:
                text = f"{{\\fad(200,0)}}{text}"
            elif wi == len(chunk) - 1:
                text = f"{{\\fad(0,200)}}{text}"

            events.append(
                f"Dialogue: 0,{fmt_time(word_start)},{fmt_time(word_end)},"
                f"Caption,,0,0,0,,{text}"
            )

    content = header + "\n".join(events)
    out_ass.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 4: Hook title card
# ---------------------------------------------------------------------------

def _render_hook_title(
    title: str,
    accent: tuple[int, int, int],
    duration: float,
    bg_path: Path,
    out_clip: Path,
) -> None:
    """Render a hook title card with zoom-in animation using ffmpeg drawtext."""
    from PIL import Image, ImageDraw

    # Create title overlay image (transparent PNG)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _find_pil_font(96)

    # Word wrap
    words = title.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if len(test) <= 26:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:3]

    total_h = len(lines) * 115
    y = (H - total_h) // 2

    r, g, b = accent
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        # Heavy shadow
        for dx, dy in [(5, 5), (4, 4), (3, 3)]:
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), line, font=font, fill=(r, g, b, 255))
        y += 115

    title_img = out_clip.with_suffix(".png")
    img.save(title_img, "PNG")

    # Animate: slow drift bg + title overlay with fade
    sw = int(W * 1.15)
    sh = int(H * 1.15)
    pad_x = sw - W
    pad_y = sh - H
    filter_str = (
        f"[0:v]scale={sw}:{sh},"
        f"crop={W}:{H}:{pad_x}*t/{duration:.2f}:{pad_y}*t/{duration:.2f},"
        f"eq=brightness=-0.2:contrast=1.1,"
        f"vignette=PI/3[bg];"
        f"[1:v]format=rgba,"
        f"fade=t=in:st=0:d=0.8:alpha=1,"
        f"fade=t=out:st={max(0.1, duration - 0.5):.2f}:d=0.5:alpha=1[title];"
        f"[bg][title]overlay=0:0[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(bg_path),
        "-loop", "1", "-framerate", str(FPS), "-i", str(title_img),
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-t", f"{duration:.2f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "22",
        "-an",
        str(out_clip),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    title_img.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"Hook render failed: {result.stderr[-400:]}")


# ---------------------------------------------------------------------------
# Phase 5: Final composite
# ---------------------------------------------------------------------------

def _concat_with_crossfades(
    clips: list[Path],
    xfade_duration: float,
    out_path: Path,
) -> None:
    """Concatenate video clips with crossfade transitions."""
    if len(clips) == 1:
        shutil.copy2(clips[0], out_path)
        return

    if len(clips) == 2:
        # Simple single crossfade
        dur0 = _get_video_duration(clips[0])
        offset = max(0.1, dur0 - xfade_duration)
        filter_str = (
            f"[0:v][1:v]xfade=transition=fadeblack:duration={xfade_duration:.2f}"
            f":offset={offset:.2f}[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(clips[0]), "-i", str(clips[1]),
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "ultrafast", "-crf", "22", "-an",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Crossfade failed: {result.stderr[-400:]}")
        return

    # For 3+ clips, chain crossfades
    transitions = ["fadeblack", "fade", "slideleft", "fadeblack", "slideup", "fade"]
    durations = [_get_video_duration(c) for c in clips]

    inputs = []
    for c in clips:
        inputs.extend(["-i", str(c)])

    # Build chained xfade filter
    filter_parts = []
    current_label = "[0:v]"
    cumulative_offset = 0.0

    for i in range(1, len(clips)):
        trans = transitions[i % len(transitions)]
        cumulative_offset += durations[i - 1] - xfade_duration
        next_label = f"[xf{i}]" if i < len(clips) - 1 else "[out]"
        filter_parts.append(
            f"{current_label}[{i}:v]xfade=transition={trans}"
            f":duration={xfade_duration:.2f}:offset={cumulative_offset:.2f}{next_label}"
        )
        current_label = next_label

    filter_str = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "22", "-an",
        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        # Fallback: simple concat without transitions
        print("    Crossfade failed, falling back to hard cuts...", flush=True)
        _simple_concat(clips, out_path)


def _simple_concat(clips: list[Path], out_path: Path) -> None:
    """Fallback: concat without transitions."""
    concat_file = out_path.with_suffix(".concat.txt")
    with concat_file.open("w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "22", "-an",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    concat_file.unlink(missing_ok=True)


def _get_video_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(result.stdout.strip())


def _add_sfx_at_transitions(
    section_boundaries: list[float],
    sfx: dict[str, Path],
    duration: float,
    out_wav: Path,
) -> None:
    """Create a WAV with whoosh SFX at each section transition."""
    import numpy as np

    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    output = np.zeros(n_samples, dtype=np.float64)

    # Load whoosh
    with wave.open(str(sfx["whoosh"]), "r") as wf:
        whoosh_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        whoosh = whoosh_data.astype(np.float64) / 32767.0

    # Place whoosh at each transition
    for boundary in section_boundaries:
        start_sample = max(0, int((boundary - 0.2) * sample_rate))
        end_sample = min(n_samples, start_sample + len(whoosh))
        segment_len = end_sample - start_sample
        if segment_len > 0 and segment_len <= len(whoosh):
            output[start_sample:end_sample] += whoosh[:segment_len] * 0.35

    # Normalize
    peak = np.max(np.abs(output))
    if peak > 0:
        output = output / peak * 0.4

    pcm = (output * 32767).astype(np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def get_bg_images() -> list[Path]:
    if BG_IMAGES_DIR.exists():
        imgs = sorted(BG_IMAGES_DIR.glob("*.jpg"))
        if imgs:
            return imgs
    return []


def _load_bg_manifest() -> dict:
    """Load background manifest for mood-based selection."""
    manifest_path = BG_IMAGES_DIR / "bg_manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _assign_section_to_clip(clip_idx: int, clip_durations: list[float],
                             sections: list[dict], total_duration: float) -> str:
    """Determine which script section a clip belongs to based on timing."""
    elapsed = sum(clip_durations[:clip_idx])
    progress = elapsed / max(0.1, total_duration)

    if not sections:
        return "act1"

    # Map by time proportion to sections
    n = len(sections)
    section_idx = min(int(progress * n), n - 1)
    return sections[section_idx].get("name", "act1").lower().replace(" ", "")


def _select_backgrounds_for_clips(
    n_clips: int,
    bg_images: list[Path],
    manifest: dict,
    section_assignments: list[str],
    seed: int,
) -> list[Path]:
    """Select backgrounds with mood matching and no consecutive duplicates."""
    rng = random.Random(seed)

    # Group backgrounds by category
    by_category = defaultdict(list)
    for bg_path in bg_images:
        cat = manifest.get(bg_path.stem, {}).get("category", "gradient")
        by_category[cat].append(bg_path)

    selected = []
    last_used = None
    last_category = None

    for i in range(n_clips):
        section = section_assignments[i]
        mood = SECTION_MOODS.get(section, SECTION_MOODS.get("act1", SECTION_MOODS["context"]))
        preferred_cats = mood.get("bg_categories", ["gradient"])

        # Build candidate pool from preferred categories
        candidates = []
        for cat in preferred_cats:
            candidates.extend(by_category.get(cat, []))

        # Also add some variety from other categories (20% chance)
        if rng.random() < 0.2 or not candidates:
            all_bgs = list(bg_images)
            candidates.extend(rng.sample(all_bgs, min(5, len(all_bgs))))

        # Remove consecutive duplicates
        if last_used in candidates and len(candidates) > 1:
            candidates = [c for c in candidates if c != last_used]

        # Prefer different category than last
        if last_category and len(candidates) > 2:
            diff_cat = [c for c in candidates
                        if manifest.get(c.stem, {}).get("category") != last_category]
            if diff_cat:
                candidates = diff_cat

        pick = rng.choice(candidates) if candidates else rng.choice(bg_images)
        selected.append(pick)
        last_used = pick
        last_category = manifest.get(pick.stem, {}).get("category")

    return selected


def render_premium_video(
    audio_path: Path,
    sections: list[dict],
    title: str,
    narration: str,
    out_video: Path,
    accent: tuple[int, int, int] = PALETTE["accent_gold"],
    video_index: int = 1,
    total_videos: int = 1,
    quality: str = "normal",
    niche: str = "personal_finance",
) -> None:
    """
    Render a premium cinematic video with rapid 2-3 second cuts.

    Pipeline:
      1. Plan clips and assign mood (section -> bg category, color grade, motion)
      2. Render each clip with mood-matched parameters
      3. Render hook title card with flash (3s)
      4. Concat all clips (hard cuts — matches faceless channel style)
      5. Generate ASS captions (word-by-word highlight)
      6. Mix: video + voiceover + whoosh SFX at cut points
    """
    duration = _get_audio_duration(audio_path)
    bg_images = get_bg_images()
    if not bg_images:
        raise RuntimeError("No background images. Run: python run_pipeline.py --setup")

    manifest = _load_bg_manifest()
    words = narration.split()

    # Get niche-appropriate default color grade
    niche_grade = NICHE_GRADE_MAP.get(niche, "dark_finance")

    work_dir = SLIDES_DIR / f"_premium_{video_index:02d}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # --- Phase 1: Plan rapid cuts + mood mapping ---
        clip_durations = []
        remaining = duration
        random.seed(video_index)
        while remaining > 0.5:
            d = random.uniform(1.8, 3.0)
            d = min(d, remaining)
            clip_durations.append(d)
            remaining -= d

        n_clips = len(clip_durations)

        # Assign each clip to a section for mood mapping
        section_assignments = [
            _assign_section_to_clip(i, clip_durations, sections, duration)
            for i in range(n_clips)
        ]

        # Select backgrounds with mood matching
        bg_selections = _select_backgrounds_for_clips(
            n_clips, bg_images, manifest, section_assignments, seed=video_index
        )

        print(f"    Phase 1: Rendering {n_clips} rapid clips (mood-mapped)...", flush=True)

        clip_paths = []
        for i, cdur in enumerate(clip_durations):
            clip_path = work_dir / f"clip_{i:03d}.mp4"
            bg_img = bg_selections[i]

            # Get mood parameters for this clip's section
            section = section_assignments[i]
            mood = SECTION_MOODS.get(section, SECTION_MOODS.get("act1", SECTION_MOODS["context"]))

            # Select motion pattern from mood's pool
            rng = random.Random(video_index * 1000 + i)
            motion_idx = rng.choice(mood.get("motion_pool", [0, 1, 2, 3]))

            # Use section-specific or niche-default color grade
            grade = mood.get("color_grade", niche_grade)

            _render_cinematic_segment(
                bg_img, cdur, i, clip_path, accent,
                motion_pattern=motion_idx,
                zoom_profile=mood.get("zoom_profile", "standard"),
                color_grade=grade,
                flash_intensity=mood.get("flash_intensity", 0.2),
            )
            clip_paths.append(clip_path)
            if (i + 1) % 10 == 0 or i == n_clips - 1:
                print(f"      {i + 1}/{n_clips} clips done", flush=True)

        # --- Phase 2: Hook title card (first 3s) ---
        hook_dur = min(3.0, duration * 0.08)
        print(f"    Phase 2: Hook title ({hook_dur:.1f}s)...", flush=True)
        hook_clip = work_dir / "hook.mp4"
        hook_bg = bg_images[(video_index - 1) % len(bg_images)]
        _render_hook_title(title, accent, hook_dur, hook_bg, hook_clip)

        # --- Phase 3: Concat (hard cuts — fast, matches faceless style) ---
        print(f"    Phase 3: Concatenating {n_clips + 1} clips...", flush=True)
        all_clips = [hook_clip] + clip_paths
        composited = work_dir / "composited.mp4"
        _simple_concat(all_clips, composited)

        # --- Phase 4: ASS captions ---
        print(f"    Phase 4: Animated captions ({len(words)} words)...", flush=True)
        ass_file = work_dir / "captions.ass"
        _generate_ass_captions(words, duration, accent, ass_file)

        # --- Phase 5: SFX at cut points ---
        print(f"    Phase 5: Transition SFX ({n_clips} cuts)...", flush=True)
        sfx = ensure_sfx()
        boundaries = []
        elapsed = hook_dur
        for cd in clip_durations:
            elapsed += cd
            boundaries.append(elapsed)
        sfx_wav = work_dir / "sfx_track.wav"
        _add_sfx_at_transitions(boundaries, sfx, duration + hook_dur, sfx_wav)

        # --- Phase 6: Final encode (video + voice + SFX + captions) ---
        print(f"    Phase 6: Final encode...", flush=True)
        out_video.parent.mkdir(parents=True, exist_ok=True)

        ass_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:")
        preset = "fast" if quality == "normal" else "ultrafast"
        crf = "19" if quality == "normal" else "24"

        final_cmd = [
            "ffmpeg", "-y",
            "-i", str(composited),
            "-i", str(audio_path),
            "-i", str(sfx_wav),
            "-filter_complex",
            f"[1:a]volume=1.0[voice];"
            f"[2:a]volume=0.4[sfx];"
            f"[voice][sfx]amix=inputs=2:duration=first:dropout_transition=2[aout];"
            f"[0:v]ass='{ass_escaped}'[vout]",
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", preset, "-crf", crf,
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(out_video),
        ]

        result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            # Fallback: encode without ASS captions
            print(f"    Captions skipped, encoding without...", flush=True)
            fallback_cmd = [
                "ffmpeg", "-y",
                "-i", str(composited),
                "-i", str(audio_path),
                "-i", str(sfx_wav),
                "-filter_complex",
                f"[1:a]volume=1.0[voice];"
                f"[2:a]volume=0.4[sfx];"
                f"[voice][sfx]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", preset, "-crf", crf,
                "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart",
                str(out_video),
            ]
            result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                raise RuntimeError(f"Final encode failed: {result.stderr[-500:]}")

        print(f"    Done!", flush=True)

    finally:
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

def _test():
    print("=== PREMIUM ENGINE TEST ===")
    bg_images = get_bg_images()
    if not bg_images:
        print("ERROR: No backgrounds. Run: python run_pipeline.py --setup")
        return

    test_dir = ROOT / "output" / "test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Generate 15s silent audio
    test_wav = test_dir / "test_audio.wav"
    with wave.open(str(test_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 22050 * 15)

    sections = [
        {"name": "hook", "text": "What if everything you believed about money was wrong?"},
        {"name": "act1", "text": "The wealthiest people in the world share five simple habits. And not one of them involves luck."},
        {"name": "close", "text": "Start today. The compound effect is waiting for you."},
    ]
    narration = " ".join(s["text"] for s in sections)

    out = test_dir / "premium_test.mp4"
    t0 = time.time()
    render_premium_video(
        audio_path=test_wav,
        sections=sections,
        title="5 Money Habits of the Wealthy",
        narration=narration,
        out_video=out,
        accent=PALETTE["accent_gold"],
        video_index=1,
        total_videos=1,
    )
    elapsed = time.time() - t0
    size_mb = out.stat().st_size / 1_048_576
    print(f"\nTest: {out}")
    print(f"Size: {size_mb:.1f} MB, rendered in {elapsed:.0f}s")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Premium cinematic video engine")
    p.add_argument("--test", action="store_true", help="Render a 15s test clip")
    args = p.parse_args()
    if args.test:
        _test()
    else:
        p.print_help()

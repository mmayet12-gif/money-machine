#!/usr/bin/env python3
"""
YouTube Video Pipeline — robust, self-validating
================================================

Turns .txt scripts in C:\\money-machine\\scripts\\ into upload-ready MP4s.

Run order:
    python run_pipeline.py --check       # validate environment only, do nothing
    python run_pipeline.py --setup       # create folders + download Piper if missing
    python run_pipeline.py               # run the full pipeline
    python run_pipeline.py --resume      # skip videos already done (default)
    python run_pipeline.py --redo 03     # force re-render video 03
    python run_pipeline.py --only 05     # process just video 05

Everything is fail-soft: one bad script will not stop the other 19.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import wave
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these paths if your project lives elsewhere
# ---------------------------------------------------------------------------
ROOT = Path(r"C:\money-machine")

SCRIPTS_DIR    = ROOT / "scripts"
VIDEOS_DIR     = ROOT / "output" / "videos"
AUDIO_DIR      = ROOT / "output" / "audio"
METADATA_DIR   = ROOT / "output" / "metadata"
LOGS_DIR       = ROOT / "output" / "logs"
SLIDES_DIR     = ROOT / "output" / "slides"      # working dir, can be wiped
PIPER_DIR      = ROOT / "tools" / "piper"
ASSETS_DIR     = ROOT / "assets"

PROGRESS_FILE  = LOGS_DIR / "progress.json"
ERROR_LOG      = LOGS_DIR / "errors.log"

PIPER_EXE      = PIPER_DIR / "piper.exe"
PIPER_MODEL    = PIPER_DIR / "en_US-lessac-high.onnx"
PIPER_CONFIG   = PIPER_DIR / "en_US-lessac-high.onnx.json"
BG_MUSIC       = ASSETS_DIR / "background_music.mp3"
BG_IMAGES_DIR  = ASSETS_DIR / "backgrounds"

# Required Python packages — name on pip vs name on import can differ
REQUIRED_PACKAGES = [
    ("moviepy",  "moviepy.editor", "1.0.3"),
    ("Pillow",   "PIL",            None),
    ("numpy",    "numpy",          None),
    ("requests", "requests",       None),
    ("tqdm",     "tqdm",           None),
    ("pydub",    "pydub",          None),
    ("gTTS",     "gtts",           None),
    ("edge-tts", "edge_tts",       None),
]

PIPER_DOWNLOADS = {
    "model": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
        "en/en_US/lessac/high/en_US-lessac-high.onnx",
        PIPER_MODEL,
        60_000_000,  # ~60MB expected min size
    ),
    "config": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
        "en/en_US/lessac/high/en_US-lessac-high.onnx.json",
        PIPER_CONFIG,
        500,         # tiny JSON, just sanity-check non-empty
    ),
    "exe_zip": (
        "https://github.com/rhasspy/piper/releases/download/"
        "2023.11.14-2/piper_windows_amd64.zip",
        PIPER_DIR / "piper_windows_amd64.zip",
        5_000_000,
    ),
}

# Color palette — section name -> RGB background
SECTION_BG = {
    "hook":    (13, 13, 13),
    "context": (15, 23, 42),
    "act1":    (10, 10, 30),
    "act2":    (10, 20, 20),
    "act3":    (20, 10, 10),
    "close":   (13, 13, 13),
}
DEFAULT_BG = (17, 24, 39)

# Accent color cycle, hex -> RGB
ACCENT_PALETTE = [
    (245, 158, 11),   # amber
    (239, 68,  68),   # red
    (34,  197, 94),   # green
    (59,  130, 246),  # blue
    (236, 72,  153),  # pink
]

WINDOWS_FONTS = ["arialbd.ttf", "calibrib.ttf", "verdanab.ttf", "tahomabd.ttf"]

# Luxury lifestyle search terms — backgrounds downloaded once during --setup
LUXURY_BG_QUERIES = [
    "luxury+mansion+exterior",
    "ferrari+lamborghini+supercar",
    "private+jet+luxury+interior",
    "luxury+yacht+ocean",
    "gold+cash+money+wealth",
    "penthouse+city+skyline+night",
    "luxury+swimming+pool+villa",
    "rolls+royce+luxury+car",
    "rolex+gold+watch+luxury",
    "mansion+interior+wealthy",
    "private+island+tropical+luxury",
    "stock+market+success+wealth",
]

# ---------------------------------------------------------------------------
# Tiny logger
# ---------------------------------------------------------------------------
def log(msg: str, level: str = "INFO") -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {level:5s} {msg}", flush=True)

def log_error(msg: str, exc: BaseException | None = None) -> None:
    log(msg, "ERROR")
    if ERROR_LOG.parent.exists():
        with ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n\n=== {datetime.now().isoformat()} ===\n")
            f.write(msg + "\n")
            if exc is not None:
                f.write("".join(traceback.format_exception(exc)))


# ---------------------------------------------------------------------------
# STEP 1: Folder validation + creation
# ---------------------------------------------------------------------------
def ensure_folders() -> None:
    for d in [SCRIPTS_DIR, VIDEOS_DIR, AUDIO_DIR, METADATA_DIR,
              LOGS_DIR, SLIDES_DIR, PIPER_DIR, ASSETS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    log(f"Folder structure verified at {ROOT}")


# ---------------------------------------------------------------------------
# STEP 2: Python package validation
# ---------------------------------------------------------------------------
def check_packages(install_if_missing: bool = False) -> list[str]:
    """Return list of missing pip names. Optionally pip-install them."""
    import importlib
    missing = []
    for pip_name, import_name, _version in REQUIRED_PACKAGES:
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)

    if missing and install_if_missing:
        log(f"Installing missing packages: {', '.join(missing)}")
        # Don't pin moviepy — version 1.0.3 has Pillow 10 ANTIALIAS bug;
        # newer 2.x is what we actually want. We pin only if user asked.
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", *missing]
        subprocess.run(cmd, check=True)
        # Re-check
        return check_packages(install_if_missing=False)

    if missing:
        log(f"Missing packages: {', '.join(missing)}", "WARN")
        log("Run: pip install " + " ".join(missing), "WARN")
    else:
        log("All required Python packages are installed")
    return missing


# ---------------------------------------------------------------------------
# STEP 3: Piper TTS download with validation
# ---------------------------------------------------------------------------
def download_file(url: str, dest: Path, min_size: int) -> bool:
    """Download with progress bar. Validates size after. Returns True on success."""
    try:
        import requests
        from tqdm import tqdm
    except ImportError:
        log("requests/tqdm not installed yet — run --setup after pip install", "ERROR")
        return False

    if dest.exists() and dest.stat().st_size >= min_size:
        log(f"Already have {dest.name} ({dest.stat().st_size:,} bytes)")
        return True

    log(f"Downloading {url} → {dest.name}")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=dest.name
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
    except Exception as e:
        log_error(f"Download failed for {url}: {e}", e)
        if dest.exists():
            dest.unlink()
        return False

    if dest.stat().st_size < min_size:
        log_error(f"{dest.name} downloaded but size is suspiciously small")
        return False
    return True


def setup_piper() -> bool:
    """Download Piper model, config, and Windows binary. Best-effort."""
    ok_model  = download_file(*PIPER_DOWNLOADS["model"])
    ok_config = download_file(*PIPER_DOWNLOADS["config"])
    ok_zip    = download_file(*PIPER_DOWNLOADS["exe_zip"])

    if ok_zip and not PIPER_EXE.exists():
        # Extract piper.exe out of the zip
        import zipfile
        zip_path = PIPER_DOWNLOADS["exe_zip"][1]
        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                # Find piper.exe wherever it is in the archive
                exe_member = next((n for n in names if n.endswith("piper.exe")), None)
                if exe_member is None:
                    log_error("piper.exe not found in zip")
                    return False
                # Extract everything to PIPER_DIR (Piper needs sibling DLLs)
                zf.extractall(PIPER_DIR)
                # Move piper.exe to a known location at PIPER_DIR/piper.exe
                extracted = PIPER_DIR / exe_member
                if extracted != PIPER_EXE:
                    shutil.copy2(extracted, PIPER_EXE)
            log(f"Piper extracted to {PIPER_DIR}")
        except Exception as e:
            log_error(f"Failed to extract Piper zip: {e}", e)
            return False

    if PIPER_EXE.exists() and PIPER_MODEL.exists() and PIPER_CONFIG.exists():
        log("Piper TTS ready")
        return True
    log("Piper not fully available — gTTS fallback will be used", "WARN")
    return False


# ---------------------------------------------------------------------------
# STEP 3b: Background image downloader
# ---------------------------------------------------------------------------
def _generate_luxury_bg(dest: Path, theme: dict) -> None:
    """Generate a luxury-themed gradient background with abstract shapes."""
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np

    W, H = 1920, 1080
    arr = np.zeros((H, W, 3), dtype=np.float64)

    c1 = np.array(theme["top"], dtype=np.float64)
    c2 = np.array(theme["bottom"], dtype=np.float64)
    for y in range(H):
        t = y / H
        # Smooth S-curve gradient
        t = t * t * (3 - 2 * t)
        arr[y, :] = c1 * (1 - t) + c2 * t

    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)

    # Add subtle geometric shapes (bokeh / lens flare)
    import random
    random.seed(hash(dest.stem))
    accent = theme.get("accent", (255, 215, 0))
    for _ in range(random.randint(8, 18)):
        cx = random.randint(0, W)
        cy = random.randint(0, H)
        r = random.randint(30, 200)
        alpha = random.randint(8, 35)
        color = (accent[0], accent[1], accent[2], alpha)
        shape_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shape_draw = ImageDraw.Draw(shape_img)
        shape_draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)
        shape_img = shape_img.filter(ImageFilter.GaussianBlur(radius=r // 3))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, shape_img)
        img = img.convert("RGB")

    # Diagonal gold/accent streaks
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(2, 5)):
        x1 = random.randint(-200, W)
        y1 = random.randint(-100, H)
        length = random.randint(300, 800)
        draw.line([(x1, y1), (x1 + length, y1 + length // 2)],
                  fill=(*accent, 15), width=random.randint(1, 3))

    img.save(dest, "JPEG", quality=92)


LUXURY_BG_THEMES = [
    {"top": (10, 10, 30), "bottom": (0, 0, 0), "accent": (255, 215, 0)},    # gold/black
    {"top": (15, 5, 25), "bottom": (5, 0, 10), "accent": (200, 160, 255)},   # purple luxury
    {"top": (0, 20, 40), "bottom": (0, 5, 15), "accent": (0, 200, 255)},     # ocean blue
    {"top": (25, 10, 5), "bottom": (5, 0, 0), "accent": (255, 120, 50)},     # rich amber
    {"top": (5, 25, 15), "bottom": (0, 8, 5), "accent": (50, 255, 150)},     # emerald
    {"top": (20, 20, 20), "bottom": (0, 0, 0), "accent": (255, 255, 255)},   # silver/black
    {"top": (30, 15, 0), "bottom": (10, 5, 0), "accent": (255, 200, 80)},    # bronze gold
    {"top": (10, 0, 20), "bottom": (3, 0, 8), "accent": (255, 80, 180)},     # magenta luxury
    {"top": (0, 15, 30), "bottom": (0, 5, 12), "accent": (100, 200, 255)},   # steel blue
    {"top": (20, 10, 10), "bottom": (5, 2, 2), "accent": (255, 80, 80)},     # ruby
    {"top": (15, 20, 10), "bottom": (5, 8, 2), "accent": (180, 255, 100)},   # lime wealth
    {"top": (25, 20, 5), "bottom": (8, 5, 0), "accent": (255, 230, 130)},    # champagne
]


def download_backgrounds() -> list[Path]:
    """Generate cinematic backgrounds using the premium bg_generator."""
    BG_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Try the new premium generator first (44 backgrounds, 9 categories)
    try:
        from bg_generator import generate_all_backgrounds
        log("  Using premium bg_generator (44 backgrounds, 9 categories)")
        return generate_all_backgrounds(BG_IMAGES_DIR)
    except Exception as e:
        log(f"  Premium bg_generator failed ({e}), using legacy generator", "WARN")

    # Legacy fallback
    images: list[Path] = []
    for i, theme in enumerate(LUXURY_BG_THEMES):
        dest = BG_IMAGES_DIR / f"bg_{i:02d}.jpg"
        if dest.exists() and dest.stat().st_size > 10_000:
            log(f"  Background {i + 1:02d}/{len(LUXURY_BG_THEMES)}: already cached ({dest.name})")
            images.append(dest)
            continue
        log(f"  Generating background {i + 1:02d}/{len(LUXURY_BG_THEMES)}")
        try:
            _generate_luxury_bg(dest, theme)
            images.append(dest)
            log(f"    ✓ Saved {dest.name}")
        except Exception as e:
            log(f"    ⚠ Generation failed: {e}", "WARN")

    return images


# ---------------------------------------------------------------------------
# STEP 4a: Script parser
# ---------------------------------------------------------------------------
SECTION_HEADERS = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?(hook|context|act\s*[123]|close|"
    r"closing|outro|intro|conclusion|cta)\b.*$",
    re.IGNORECASE,
)

STRIP_PATTERNS = [
    re.compile(r"\[VISUAL:[^\]]*\]",        re.IGNORECASE),
    re.compile(r"\[SFX:[^\]]*\]",           re.IGNORECASE),
    re.compile(r"\[SOUND EFFECT:[^\]]*\]",  re.IGNORECASE),
    re.compile(r"\[B-?ROLL:[^\]]*\]",       re.IGNORECASE),
    re.compile(r"\[MUSIC:[^\]]*\]",         re.IGNORECASE),
    re.compile(r"\[PAUSE(?:-LONG)?\]",      re.IGNORECASE),
    re.compile(r"\[BREATHE\]",              re.IGNORECASE),
    re.compile(r"\(\d+:\d+(?:\s*-\s*\d+:\d+)?\)"),     # (0:00-0:15)
    re.compile(r"\[\d+:\d+\]"),                         # [1:30]
    re.compile(r"\*+\s*Pattern Interrupt\s*\*+\s*[—\-:]*\s*", re.IGNORECASE),
]

SPEAKER_LABEL = re.compile(
    r"^(?:Narrator|Host|Voiceover|Voice Over|VO|Announcer|Speaker|You)\s*:\s*",
    re.IGNORECASE | re.MULTILINE,
)

META_LINE = re.compile(
    r"^\s*(?:Word Count|This script|Note|THE END|END|Total runtime|Duration)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)

DIVIDER_LINE = re.compile(r"^\s*[-=*_]{3,}\s*$", re.MULTILINE)


def parse_script(path: Path) -> dict:
    """
    Returns:
        {
          'title': str,
          'narration': str,            # clean speakable text (whole video)
          'sections': [                # split for slide rotation
              {'name': 'hook', 'text': '...'},
              ...
          ],
        }
    """
    raw = path.read_text(encoding="utf-8", errors="replace")

    # 1. Pull title from first **Title:** or **Script:** line, or filename.
    #    Handles both **Title:** value AND **Title**: value
    title = None
    for line in raw.splitlines()[:20]:
        m = re.search(
            r"\*\*\s*(?:Title|Script)\s*:?\s*\*\*\s*:?\s*(.+)|"
            r"\*\*\s*(?:Title|Script)\s*\*\*\s*:\s*(.+)",
            line, re.IGNORECASE,
        )
        if m:
            title = (m.group(1) or m.group(2) or "").strip().strip('"').strip("*").strip()
            if title:
                break
    if not title:
        # Strip the leading "01_" video-number prefix if present
        stem = re.sub(r"^\d+[_\-\s]+", "", path.stem)
        title = stem.replace("_", " ").replace("-", " ").strip() or path.stem

    # 2. Walk lines, splitting into sections by ## headers.
    #    Skip the **Title:** line itself so it isn't spoken.
    sections: list[dict] = []
    current = {"name": "intro", "lines": []}
    title_line_re = re.compile(
        r"\*\*\s*(?:Title|Script)\s*:?\s*\*\*|\*\*\s*(?:Title|Script)\s*\*\*\s*:",
        re.IGNORECASE,
    )

    for line in raw.splitlines():
        # Skip the title declaration line itself
        if title_line_re.search(line):
            continue
        # Section header?
        h = SECTION_HEADERS.match(line.strip())
        if h:
            if current["lines"]:
                sections.append(current)
            section_name = h.group(1).lower().replace(" ", "")
            current = {"name": section_name, "lines": []}
            continue
        current["lines"].append(line)
    if current["lines"]:
        sections.append(current)

    # 3. Clean each section
    cleaned_sections = []
    for sec in sections:
        text = "\n".join(sec["lines"])

        for pat in STRIP_PATTERNS:
            text = pat.sub("", text)
        text = SPEAKER_LABEL.sub("", text)
        text = META_LINE.sub("", text)
        text = DIVIDER_LINE.sub("", text)

        # Remove markdown bold/italic markers but keep words
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)

        # Strip leading/trailing quote marks per line
        text = "\n".join(ln.strip().strip('"').strip("'") for ln in text.splitlines())

        # Collapse whitespace
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if text:
            cleaned_sections.append({"name": sec["name"], "text": text})

    # 4. Full narration = concatenation
    narration = "\n\n".join(s["text"] for s in cleaned_sections).strip()

    if not narration:
        raise ValueError(f"Script {path.name} produced empty narration after cleaning")

    return {"title": title, "narration": narration, "sections": cleaned_sections}


# ---------------------------------------------------------------------------
# STEP 4b: TTS engines, tried in order
# ---------------------------------------------------------------------------
def tts_piper(text: str, out_wav: Path) -> bool:
    if not (PIPER_EXE.exists() and PIPER_MODEL.exists()):
        return False
    try:
        proc = subprocess.run(
            [str(PIPER_EXE),
             "--model", str(PIPER_MODEL),
             "--output_file", str(out_wav),
             "--length_scale", "1.05"],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=600,
        )
        if proc.returncode != 0:
            log(f"Piper stderr: {proc.stderr.decode('utf-8', 'replace')[:500]}", "WARN")
            return False
        return out_wav.exists() and out_wav.stat().st_size > 1024
    except Exception as e:
        log_error(f"Piper failed: {e}", e)
        return False


def tts_gtts(text: str, out_wav: Path) -> bool:
    try:
        from gtts import gTTS
    except ImportError:
        return False
    try:
        mp3_path = out_wav.with_suffix(".mp3")
        # gTTS chokes on extremely long single requests; split if needed
        chunks = [text[i:i + 4500] for i in range(0, len(text), 4500)] or [text]
        if len(chunks) == 1:
            gTTS(text=chunks[0], lang="en").save(str(mp3_path))
        else:
            from pydub import AudioSegment
            combined = AudioSegment.silent(duration=0)
            for i, ch in enumerate(chunks):
                tmp = out_wav.with_name(f"_part{i}.mp3")
                gTTS(text=ch, lang="en").save(str(tmp))
                combined += AudioSegment.from_mp3(tmp)
                tmp.unlink(missing_ok=True)
            combined.export(mp3_path, format="mp3")

        # Convert to WAV (MoviePy is happier with WAV)
        try:
            from pydub import AudioSegment
            AudioSegment.from_mp3(mp3_path).export(out_wav, format="wav")
            mp3_path.unlink(missing_ok=True)
        except Exception:
            # No pydub or no ffmpeg — keep MP3, rename so caller can find it
            shutil.move(mp3_path, out_wav.with_suffix(".mp3"))
            return False if not out_wav.with_suffix(".mp3").exists() else True
        return out_wav.exists() and out_wav.stat().st_size > 1024
    except Exception as e:
        log_error(f"gTTS failed: {e}", e)
        return False


def tts_silence(text: str, out_wav: Path) -> bool:
    """Last-resort: write silence proportional to word count (~150 wpm)."""
    words = max(20, len(text.split()))
    seconds = max(10.0, words / 150.0 * 60.0)
    framerate = 22050
    n_frames = int(seconds * framerate)
    try:
        with wave.open(str(out_wav), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(framerate)
            w.writeframes(b"\x00\x00" * n_frames)
        log(f"WROTE SILENCE for {out_wav.name} — RE-RUN AUDIO LATER", "WARN")
        return True
    except Exception as e:
        log_error(f"Even silence WAV failed: {e}", e)
        return False


def _add_narration_pauses(text: str) -> str:
    """Insert SSML-style pauses after sentences for cinematic pacing."""
    import re
    # Add a brief pause after every sentence-ending punctuation
    text = re.sub(r'([.!?])\s+', r'\1 ... ', text)
    # Add longer pause after paragraph breaks
    text = re.sub(r'\n\n+', ' ...... ', text)
    return text


def tts_edge(text: str, out_wav: Path) -> bool:
    """Microsoft Edge Neural TTS — cinematic documentary voice.

    Uses en-US-ChristopherNeural with:
      - Slower rate (-18%) for deliberate, authoritative pacing
      - Lower pitch (-3Hz) for deeper, richer tone
      - Sentence pauses for emphasis
    """
    try:
        import edge_tts
    except ImportError:
        return False
    try:
        import asyncio
        mp3_path = out_wav.with_suffix(".mp3")

        cinematic_text = _add_narration_pauses(text)

        async def _speak() -> None:
            communicate = edge_tts.Communicate(
                cinematic_text,
                "en-US-ChristopherNeural",
                rate="-18%",
                pitch="-3Hz",
            )
            await communicate.save(str(mp3_path))

        asyncio.run(_speak())

        if not mp3_path.exists() or mp3_path.stat().st_size < 1024:
            return False

        try:
            from pydub import AudioSegment
            AudioSegment.from_mp3(mp3_path).export(out_wav, format="wav")
            mp3_path.unlink(missing_ok=True)
            return out_wav.exists() and out_wav.stat().st_size > 1024
        except Exception:
            shutil.move(str(mp3_path), str(out_wav.with_suffix(".mp3")))
            return out_wav.with_suffix(".mp3").exists()
    except Exception as e:
        log_error(f"edge-tts failed: {e}", e)
        return False


def make_voiceover(text: str, out_wav: Path) -> str:
    """Returns name of engine used, or 'failed'."""
    if tts_edge(text, out_wav):
        return "edge-tts"
    if tts_piper(text, out_wav):
        return "piper"
    if tts_gtts(text, out_wav):
        return "gtts"
    if tts_silence(text, out_wav):
        return "silence"
    return "failed"


# ---------------------------------------------------------------------------
# STEP 4c: Slide builder
# ---------------------------------------------------------------------------
def find_font(size: int):
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


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        candidate = (cur + " " + w).strip()
        if len(candidate) <= max_chars:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_slide(
    slide_path: Path,
    title: str,
    section_name: str,
    body_text: str,
    accent: tuple[int, int, int],
    video_index: int,
    total_videos: int,
    bg_image_path: Path | None = None,
) -> None:
    from PIL import Image, ImageDraw

    W, H = 1920, 1080

    # Background: luxury photo with dark overlay, or solid fallback
    if bg_image_path and bg_image_path.exists():
        try:
            img = Image.open(bg_image_path).convert("RGB").resize((W, H), Image.LANCZOS)
            overlay = Image.new("RGB", (W, H), (0, 0, 0))
            img = Image.blend(img, overlay, alpha=0.58)
        except Exception:
            img = Image.new("RGB", (W, H), SECTION_BG.get(section_name.lower(), DEFAULT_BG))
    else:
        img = Image.new("RGB", (W, H), SECTION_BG.get(section_name.lower(), DEFAULT_BG))

    draw = ImageDraw.Draw(img)

    # Accent bars top + bottom
    draw.rectangle([(0, 0), (W, 10)], fill=accent)
    draw.rectangle([(0, H - 10), (W, H)], fill=accent)

    # Title with drop shadow
    title_font = find_font(82)
    title_lines = wrap_text(title, 40)[:2]
    y_cursor = 110
    for line in title_lines:
        draw.text((84, y_cursor + 4), line, font=title_font, fill=(0, 0, 0))
        draw.text((80, y_cursor), line, font=title_font, fill=accent)
        y_cursor += 102

    # Divider
    draw.rectangle([(80, y_cursor + 8), (W - 80, y_cursor + 12)], fill=accent)
    y_cursor += 54

    # Body text with drop shadow
    body_font = find_font(44)
    snippet = (body_text[:400] + "…") if len(body_text) > 400 else body_text
    for line in wrap_text(snippet, 60):
        if y_cursor > H - 150:
            break
        draw.text((84, y_cursor + 3), line, font=body_font, fill=(0, 0, 0))
        draw.text((80, y_cursor), line, font=body_font, fill=(255, 255, 255))
        y_cursor += 58

    # Footer
    foot_font = find_font(26)
    draw.text((80, H - 58),
              f"Video {video_index:02d} of {total_videos:02d}",
              font=foot_font, fill=(200, 200, 200))
    foot_right = "Personal Finance Channel"
    bbox = draw.textbbox((0, 0), foot_right, font=foot_font)
    draw.text((W - 80 - (bbox[2] - bbox[0]), H - 58),
              foot_right, font=foot_font, fill=(200, 200, 200))

    img.save(slide_path, "PNG", optimize=True)


# ---------------------------------------------------------------------------
# STEP 4d: Video assembler
# ---------------------------------------------------------------------------
def assemble_video(
    audio_path: Path,
    slide_paths: list[Path],
    out_video: Path,
    narration_text: str,
) -> None:
    # Import inside function so --check works without moviepy installed
    try:
        from moviepy.editor import (
            AudioFileClip, ImageClip, concatenate_videoclips,
            CompositeAudioClip, CompositeVideoClip, TextClip, AudioClip,
            afx,
        )
    except ImportError as e:
        raise RuntimeError(
            "moviepy is not installed. Run: pip install moviepy"
        ) from e

    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    # Per-section duration
    n = max(1, len(slide_paths))
    per_section = duration / n

    clips = [
        ImageClip(str(p)).set_duration(per_section)
        for p in slide_paths
    ]
    video = concatenate_videoclips(clips, method="compose")

    # Captions — best-effort, skip on any failure
    try:
        words = narration_text.split()
        chunk_size = 5
        chunks = [" ".join(words[i:i + chunk_size])
                  for i in range(0, len(words), chunk_size)]
        if chunks:
            chunk_dur = duration / len(chunks)
            caption_clips = []
            for i, chunk in enumerate(chunks):
                tc = (TextClip(
                        chunk,
                        fontsize=50,
                        color="white",
                        stroke_color="black",
                        stroke_width=2,
                        font="Arial-Bold",
                        method="caption",
                        size=(int(video.w * 0.85), None),
                      )
                      .set_position(("center", int(video.h * 0.83)))
                      .set_start(i * chunk_dur)
                      .set_duration(chunk_dur))
                caption_clips.append(tc)
            video = CompositeVideoClip([video, *caption_clips])
    except Exception as e:
        log(f"Captions skipped (likely missing ImageMagick): {e}", "WARN")

    # Background music (optional)
    final_audio = audio
    if BG_MUSIC.exists():
        try:
            from moviepy.editor import AudioFileClip as _AFC
            music = _AFC(str(BG_MUSIC)).fx(afx.volumex, 0.07)
            # Loop music to match video duration
            if music.duration < duration:
                from moviepy.audio.AudioClip import concatenate_audioclips
                loops = int(duration // music.duration) + 1
                music = concatenate_audioclips([music] * loops).subclip(0, duration)
            else:
                music = music.subclip(0, duration)
            final_audio = CompositeAudioClip([audio, music])
        except Exception as e:
            log(f"Background music skipped: {e}", "WARN")

    video = video.set_audio(final_audio)

    out_video.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(out_video),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="3500k",
        preset="ultrafast",
        threads=2,
        verbose=False,
        logger=None,
        temp_audiofile=str(out_video.with_suffix(".temp_audio.m4a")),
        remove_temp=True,
    )

    # Cleanup
    try:
        audio.close()
        video.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# STEP 4e: Metadata generator
# ---------------------------------------------------------------------------
DEFAULT_TAGS = [
    "personal finance", "money tips", "financial freedom", "budgeting",
    "investing for beginners", "save money", "wealth building",
    "financial advice 2026", "money management", "passive income",
    "debt payoff", "emergency fund", "index funds",
]

UPLOAD_CHECKLIST = [
    "Watch the first 30 seconds in VLC — confirm audio is clear",
    "Add a custom thumbnail (1280x720, high contrast, big text)",
    "Copy description and tags from this metadata JSON",
    "Set audience: 'No, it's not made for kids'",
    "Keep visibility = Private until reviewed, then switch to Public",
]


def make_metadata(parsed: dict, video_index: int, narration: str) -> dict:
    title = parsed["title"]
    sections = parsed["sections"]

    # First 60 words of narration
    words = narration.split()
    intro = " ".join(words[:60])

    # One-line bullet per section
    bullets = []
    for sec in sections:
        first_sentence = re.split(r"(?<=[.!?])\s+", sec["text"].strip(), maxsplit=1)[0]
        if first_sentence:
            bullets.append(f"• {first_sentence[:120]}")

    description = (
        f"{intro}…\n\n"
        f"In this video:\n" + "\n".join(bullets) + "\n\n"
        f"#PersonalFinance #MoneyTips #FinancialFreedom #Investing #Budgeting\n\n"
        f"⚠️ Disclaimer: This video is for educational purposes only and is not "
        f"financial advice. Consult a licensed financial advisor before making "
        f"investment decisions."
    )

    return {
        "title": title[:100],
        "description": description[:5000],
        "tags": [title[:30]] + DEFAULT_TAGS,
        "category_id": "27",
        "privacy_status": "private",
        "made_for_kids": False,
        "upload_checklist": UPLOAD_CHECKLIST,
        "generated_at": datetime.now().isoformat(),
        "video_index": video_index,
    }


# ---------------------------------------------------------------------------
# STEP 4f: Progress tracker
# ---------------------------------------------------------------------------
def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"completed": {}, "failed": {}}
    return {"completed": {}, "failed": {}}


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Filename sanitizer
# ---------------------------------------------------------------------------
def safe_filename(s: str, max_len: int = 45) -> str:
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:max_len] or "Untitled"


# ---------------------------------------------------------------------------
# STEP 5: Per-video processing
# ---------------------------------------------------------------------------
def process_one_script(
    script_path: Path,
    index: int,
    total: int,
    accent: tuple[int, int, int],
) -> dict:
    """Returns a result dict. Always returns — never raises."""
    t0 = time.time()
    result = {
        "script": script_path.name,
        "index": index,
        "ok": False,
        "error": None,
        "video": None,
        "duration_s": 0,
        "tts_engine": None,
    }

    try:
        log(f"[{index:02d}/{total:02d}] Parsing {script_path.name}")
        parsed = parse_script(script_path)
        title = parsed["title"]
        log(f"          Title: {title}")

        stem = f"{index:02d}_{safe_filename(title)}"

        audio_path = AUDIO_DIR / f"{stem}.wav"
        video_path = VIDEOS_DIR / f"{stem}.mp4"
        meta_path  = METADATA_DIR / f"{stem}.json"
        result["video"] = str(video_path)

        # 1. TTS
        log(f"          Generating voiceover…")
        engine = make_voiceover(parsed["narration"], audio_path)
        result["tts_engine"] = engine
        if engine == "failed":
            raise RuntimeError("All TTS engines failed")
        log(f"          TTS engine used: {engine}")

        # 2+3. Render video (premium cinematic engine)
        sections = parsed["sections"] or [{"name": "intro", "text": parsed["narration"]}]
        try:
            from premium_engine import render_premium_video, PALETTE
            log(f"          Rendering with premium engine ({len(sections)} sections)…")
            render_premium_video(
                audio_path=audio_path,
                sections=sections,
                title=title,
                narration=parsed["narration"],
                out_video=video_path,
                accent=accent,
                video_index=index,
                total_videos=total,
            )
        except Exception as ve:
            log(f"          Premium engine failed ({ve}), falling back to viral engine", "WARN")
            try:
                from viral_engine import render_viral_video
                render_viral_video(
                    audio_path=audio_path,
                    sections=sections,
                    title=title,
                    narration=parsed["narration"],
                    out_video=video_path,
                    accent=accent,
                    video_index=index,
                    total_videos=total,
                )
            except Exception as ve2:
                log(f"          Viral engine also failed ({ve2}), using static fallback", "WARN")
                slide_paths = []
                bg_images = sorted(BG_IMAGES_DIR.glob("*.jpg")) if BG_IMAGES_DIR.exists() else []
                for i, sec in enumerate(sections):
                    sp = SLIDES_DIR / f"{stem}_slide_{i:02d}.png"
                    bg_img = bg_images[(index - 1 + i) % len(bg_images)] if bg_images else None
                    build_slide(
                        sp, title, sec["name"], sec["text"],
                        accent, index, total,
                        bg_image_path=bg_img,
                    )
                    slide_paths.append(sp)
                log(f"          Rendering video ({len(slide_paths)} slides)…")
                assemble_video(audio_path, slide_paths, video_path, parsed["narration"])
                for sp in slide_paths:
                    sp.unlink(missing_ok=True)

        # 4. Metadata
        meta = make_metadata(parsed, index, parsed["narration"])
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        size_mb = video_path.stat().st_size / 1_048_576 if video_path.exists() else 0
        elapsed = time.time() - t0
        result["ok"] = True
        result["duration_s"] = round(elapsed, 1)
        log(f"          ✓ Done in {elapsed:.1f}s — {size_mb:.1f} MB")

    except Exception as e:
        elapsed = time.time() - t0
        result["error"] = f"{type(e).__name__}: {e}"
        result["duration_s"] = round(elapsed, 1)
        log(f"          ✗ FAILED: {result['error']}", "ERROR")
        log_error(f"Script {script_path.name} failed", e)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def cmd_check() -> int:
    log("=== ENVIRONMENT CHECK ===")
    ensure_folders()

    issues = 0

    # Folders
    for d in [SCRIPTS_DIR, VIDEOS_DIR, AUDIO_DIR, METADATA_DIR, LOGS_DIR]:
        log(f"  {'✓' if d.exists() else '✗'} {d}")
        if not d.exists():
            issues += 1

    # Scripts
    scripts = sorted(SCRIPTS_DIR.glob("*.txt"))
    log(f"Scripts found: {len(scripts)}")
    for s in scripts:
        log(f"    - {s.name}")
    if not scripts:
        log("No .txt scripts in C:\\money-machine\\scripts\\", "WARN")
        issues += 1

    # Packages
    missing = check_packages(install_if_missing=False)
    if missing:
        issues += 1

    # Piper
    if PIPER_EXE.exists() and PIPER_MODEL.exists():
        log("✓ Piper available (best quality)")
    else:
        log("⚠ Piper not installed — gTTS will be used (needs internet)", "WARN")

    # ffmpeg (MoviePy needs this and gTTS->WAV needs this)
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    log(f"  {'✓' if ffmpeg_ok else '⚠'} ffmpeg in PATH ({'yes' if ffmpeg_ok else 'NO — install: winget install Gyan.FFmpeg'})")
    if not ffmpeg_ok:
        log("ffmpeg missing → MoviePy will fail. Install with: winget install Gyan.FFmpeg", "WARN")

    # ImageMagick (only needed for captions)
    im_ok = shutil.which("magick") is not None or shutil.which("convert") is not None
    log(f"  {'✓' if im_ok else '⚠'} ImageMagick ({'yes' if im_ok else 'NO — captions will be skipped'})")

    # Background music (optional)
    log(f"  {'✓' if BG_MUSIC.exists() else '○'} Background music ({BG_MUSIC.name})")

    log(f"=== CHECK COMPLETE: {issues} issue(s) ===")
    return 0 if issues == 0 else 1


def cmd_setup() -> int:
    log("=== SETUP ===")
    ensure_folders()
    check_packages(install_if_missing=True)
    setup_piper()
    log("Downloading luxury background images…")
    imgs = download_backgrounds()
    log(f"Backgrounds ready: {len(imgs)} images in {BG_IMAGES_DIR}")
    log("=== SETUP COMPLETE ===")
    return 0


def cmd_run(args) -> int:
    log("=== RUN PIPELINE ===")
    ensure_folders()

    missing = check_packages(install_if_missing=False)
    if missing:
        log("Cannot run — install packages first: python run_pipeline.py --setup", "ERROR")
        return 1

    scripts = sorted(SCRIPTS_DIR.glob("*.txt"))
    if not scripts:
        log(f"No scripts in {SCRIPTS_DIR}", "ERROR")
        return 1

    # Filtering
    if args.only is not None:
        scripts = [s for i, s in enumerate(scripts, 1) if i == args.only]

    progress = load_progress()
    completed = progress.get("completed", {})
    failed_prev = progress.get("failed", {})

    results = []
    pipeline_start = time.time()

    all_scripts = sorted(SCRIPTS_DIR.glob("*.txt"))
    total_scripts = len(all_scripts)

    try:
        for idx, script in enumerate(all_scripts, 1):
            if args.only is not None and idx != args.only:
                continue
            if args.redo is not None and idx == args.redo:
                completed.pop(str(idx), None)
            if str(idx) in completed and not args.redo == idx:
                log(f"[{idx:03d}/{total_scripts}] Skipping (already done): {script.name}")
                continue

            accent = ACCENT_PALETTE[(idx - 1) % len(ACCENT_PALETTE)]
            result = process_one_script(script, idx, total_scripts, accent)
            results.append(result)

            if result["ok"]:
                completed[str(idx)] = {
                    "script": result["script"],
                    "video": result["video"],
                    "tts": result["tts_engine"],
                    "completed_at": datetime.now().isoformat(),
                }
                failed_prev.pop(str(idx), None)
            else:
                failed_prev[str(idx)] = {
                    "script": result["script"],
                    "error": result["error"],
                    "failed_at": datetime.now().isoformat(),
                }

            progress["completed"] = completed
            progress["failed"] = failed_prev
            save_progress(progress)

    except KeyboardInterrupt:
        log("Interrupted by user. Progress saved. Run again to resume.", "WARN")
        save_progress(progress)
        return 130

    # ---- Summary ----
    total_elapsed = time.time() - pipeline_start
    ok_count = sum(1 for r in results if r["ok"])
    fail_count = sum(1 for r in results if not r["ok"])

    print("\n" + "=" * 60)
    print(f"  COMPLETED: {ok_count}    FAILED: {fail_count}    TIME: {total_elapsed/60:.1f} min")
    print("=" * 60)

    if fail_count:
        print("\nFailed videos (re-run with --redo NN):")
        for r in results:
            if not r["ok"]:
                print(f"  {r['index']:02d}  {r['script']}  →  {r['error']}")

    if ok_count > 0:
        print("\n" + "═" * 55)
        print("  ALL DONE! Your videos are ready.")
        print()
        print(f"  📁 Videos:   {VIDEOS_DIR}")
        print(f"  📁 Metadata: {METADATA_DIR}")
        print()
        print("  NEXT STEPS:")
        print("  1. Open one video in VLC to check quality")
        print("  2. If audio is good → upload to YouTube as Private")
        print("  3. Add custom thumbnail (see thumbnail briefs)")
        print("  4. Review description and tags from metadata JSON")
        print("  5. Set to Public when ready")
        print("═" * 55)

    return 0 if fail_count == 0 else 2


def main() -> int:
    p = argparse.ArgumentParser(description="YouTube video pipeline")
    p.add_argument("--check",  action="store_true", help="Validate environment only")
    p.add_argument("--setup",  action="store_true", help="Install packages + download Piper")
    p.add_argument("--resume", action="store_true", help="Skip already-done videos (default)")
    p.add_argument("--redo",   type=int, metavar="N", help="Force re-render video N")
    p.add_argument("--only",   type=int, metavar="N", help="Process only video N")
    p.add_argument("--force",  action="store_true", help="Override long-form pause flag")
    args = p.parse_args()

    # ── Long-form pause guard ──────────────────────────────────────
    # Analytics show landscape (1920x1080) long-form videos get 0 views on channels
    # under 1000 subscribers. Paused until threshold reached.
    # Remove C:\money-machine\RESUME_LONGFORM to re-enable.
    pause_flag  = ROOT / "PAUSE_LONGFORM"
    resume_flag = ROOT / "RESUME_LONGFORM"
    if not args.check and not args.setup and not args.force:
        if pause_flag.exists() and not resume_flag.exists():
            print("=" * 60)
            print("  LONG-FORM PRODUCTION PAUSED")
            print("  Analytics: 73 landscape videos averaging 0.3 views each.")
            print("  YouTube algorithm won't surface long-form on channels")
            print("  under ~1,000 subscribers.")
            print("  Focus: Shorts-only until 1,000 subs milestone.")
            print()
            print("  To re-enable: delete C:\\money-machine\\PAUSE_LONGFORM")
            print("  or run with --force flag.")
            print("=" * 60)
            return 0   # Exit cleanly — not an error

    if args.check:
        return cmd_check()
    if args.setup:
        return cmd_setup()
    return cmd_run(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)

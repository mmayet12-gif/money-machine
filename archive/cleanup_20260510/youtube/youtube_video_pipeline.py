"""
YouTube Video Production Pipeline
===================================
Reads the 20 personal finance scripts and produces upload-ready .mp4 videos.

Pipeline per video:
  1. Parse script  -> extract clean narration text + section labels
  2. TTS           -> generate voiceover WAV with Piper (free, local)
  3. Visuals       -> download relevant free stock video clips (Pexels API, free key)
                      OR use generated solid-color + text slides as fallback
  4. Captions      -> burn word-by-word captions onto frames
  5. Music         -> mix royalty-free background track at low volume
  6. Assemble      -> MoviePy renders final MP4

Requirements (install once):
  pip install moviepy pillow requests pydub numpy tqdm
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

Piper TTS (free, local, no GPU needed):
  Windows: download from https://github.com/rhasspy/piper/releases
  Place piper.exe in C:\\money-machine\\tools\\piper\\
  Download voice model: en_US-lessac-high.onnx to same folder

Run:
  python youtube_video_pipeline.py

Output:
  C:\\money-machine\\youtube\\videos\\  <- final MP4s ready to upload
"""

import os
import re
import sys
import json
import time
import shutil
import subprocess
import textwrap
import requests
import threading
from pathlib import Path
from datetime import datetime

# ── Optional imports (graceful fallback if missing) ───────────────────────────
try:
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, ImageClip, TextClip,
        CompositeVideoClip, CompositeAudioClip, concatenate_videoclips,
        ColorClip
    )
    from moviepy.audio.AudioClip import AudioArrayClip
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — edit these paths to match your machine
# ══════════════════════════════════════════════════════════════════════════════

class Config:
    # Folders
    SCRIPTS_DIR   = r"C:\money-machine\youtube\runs\full_run_01\S1\"   # paste your 20 .txt files here
    OUTPUT_DIR    = r"C:\money-machine\youtube\videos"
    ASSETS_DIR    = r"C:\money-machine\youtube\assets"
    TOOLS_DIR     = r"C:\money-machine\tools"
    LOGS_DIR      = r"C:\money-machine\youtube\logs"

    # Piper TTS
    PIPER_EXE     = r"C:\money-machine\tools\piper\piper.exe"
    PIPER_MODEL   = r"C:\money-machine\tools\piper\en_US-lessac-high.onnx"

    # Video settings
    VIDEO_WIDTH   = 1920
    VIDEO_HEIGHT  = 1080
    VIDEO_FPS     = 24
    VIDEO_BITRATE = "4000k"

    # Background music (place any royalty-free mp3 here)
    # Free source: https://pixabay.com/music/search/calm%20background/
    MUSIC_FILE    = r"C:\money-machine\youtube\assets\background_music.mp3"
    MUSIC_VOLUME  = 0.08   # 8% volume — subtle background

    # Pexels API (free key — sign up at pexels.com/api)
    # Leave blank "" to skip stock footage and use slide-based visuals instead
    PEXELS_API_KEY = ""

    # Caption style
    CAPTION_FONT_SIZE  = 52
    CAPTION_COLOR      = "white"
    CAPTION_BG_ALPHA   = 0.55    # semi-transparent caption background
    CAPTION_POSITION   = ("center", 0.82)  # 82% down the screen

    # Colours for slide-based visuals (one per section type)
    SECTION_COLORS = {
        "hook":    "#0d0d0d",
        "context": "#111827",
        "act1":    "#0f172a",
        "act2":    "#0f172a",
        "act3":    "#111827",
        "close":   "#0d0d0d",
        "default": "#111827",
    }
    ACCENT_COLORS = ["#F5A623", "#EF4444", "#22C55E", "#60A5FA", "#F472B6"]


# ══════════════════════════════════════════════════════════════════════════════
# SCRIPT PARSER
# ══════════════════════════════════════════════════════════════════════════════

class ScriptParser:
    """
    Extracts clean spoken narration from the raw script files.
    Strips: [VISUAL:...], [SFX:...], **bold**, timestamps, section headers,
    pattern interrupt labels, and markdown formatting.
    Returns a list of (section_type, narration_text) tuples.
    """

    # Tags to completely remove (non-spoken)
    REMOVE_PATTERNS = [
        r'\[VISUAL[^\]]*\]',           # [VISUAL: ...]
        r'\[SFX[^\]]*\]',              # [SFX: ...]
        r'\[SOUND EFFECT[^\]]*\]',     # [SOUND EFFECT: ...]
        r'\[PAUSE[^\]]*\]',            # [PAUSE], [PAUSE-LONG]
        r'\[BREATHE\]',
        r'\[Volume[^\]]*\]',
        r'\[NARRATOR[^\]]*\]',
        r'\[Pattern Interrupt[^\]]*\]',
        r'\[VISUAL\]',
        r'\*\*Pattern Interrupt\*\*:?',
        r'Pattern Interrupt:?',
        r'\(SFX[^\)]*\)',
        r'\(Soft[^\)]*\)',
        r'\(Speaker[^\)]*\)',
        r'\(Camera[^\)]*\)',
        r'\(Soothing[^\)]*\)',
        r'\(Somber[^\)]*\)',
        r'\(Upbeat[^\)]*\)',
        r'\(Soft[^\)]*\)',
        r'\(Closing[^\)]*\)',
        r'\*\*\[.*?\]\*\*',
        r'\[.*?MUSIC.*?\]',
        r'\[.*?music.*?\]',
        r'\[EXCITED\]|\[SERIOUS\]|\[CURIOUS\]',
        r'^\s*\*\*Script:\*\*.*$',
        r'^\s*\*\*Title:\*\*.*$',
        r'^\s*Word Count:.*$',
        r'^\s*\*\*END\*\*.*$',
        r'^\s*\[THE END\].*$',
        r'^\s*\[Fade.*?\].*$',
        r'^\s*\[OUTRO.*?\].*$',
        r'^\s*Note:.*$',
        r'^\s*This script is production.*$',
    ]

    SECTION_MAP = {
        r'hook': 'hook',
        r'context': 'context',
        r'urgency': 'context',
        r'act.?1': 'act1',
        r'act.?2': 'act2',
        r'act.?3': 'act3',
        r'act.?4': 'act3',
        r'close': 'close',
        r'cta': 'close',
        r'outro': 'close',
        r'next.?video': 'close',
    }

    @classmethod
    def parse(cls, filepath: str) -> dict:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()

        # Extract title
        title = cls._extract_title(filepath, raw)

        # Split into sections
        sections = cls._split_sections(raw)

        # Extract clean text per section
        result_sections = []
        for section_type, text in sections:
            clean = cls._clean_text(text)
            if clean.strip():
                result_sections.append({
                    "type": section_type,
                    "text": clean.strip()
                })

        # Full narration (all sections combined)
        full_text = " ".join(s["text"] for s in result_sections)

        return {
            "title": title,
            "filepath": filepath,
            "sections": result_sections,
            "full_narration": full_text,
            "word_count": len(full_text.split()),
        }

    @classmethod
    def _extract_title(cls, filepath, raw):
        # Try from content
        m = re.search(r'\*\*(?:Script|Title):\*\*\s*(.+)', raw)
        if m:
            return m.group(1).strip().strip('"')
        # Try from first H1/H2
        m = re.search(r'^#+\s*(.+)', raw, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('*')
        # Fall back to filename
        name = Path(filepath).stem
        name = re.sub(r'^s1_long_\d+_', '', name)
        name = name.replace('-', ' ').replace('_', ' ').title()
        return name

    @classmethod
    def _split_sections(cls, raw):
        """Split script into labelled sections."""
        lines = raw.split('\n')
        sections = []
        current_type = 'default'
        current_lines = []

        for line in lines:
            # Detect section header
            detected = cls._detect_section(line)
            if detected:
                if current_lines:
                    sections.append((current_type, '\n'.join(current_lines)))
                current_type = detected
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_type, '\n'.join(current_lines)))

        return sections if sections else [('default', raw)]

    @classmethod
    def _detect_section(cls, line):
        clean = line.lower().strip().strip('*#[]()').strip()
        for pattern, section_type in cls.SECTION_MAP.items():
            if re.search(pattern, clean):
                return section_type
        return None

    @classmethod
    def _clean_text(cls, text):
        # Remove all non-spoken tags and markers
        for pattern in cls.REMOVE_PATTERNS:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)   # bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)         # italic
        text = re.sub(r'#+\s*', '', text)                # headers
        text = re.sub(r'^\s*[\*\-]\s+', '', text, flags=re.MULTILINE)  # bullets

        # Remove speaker labels (Narrator:, Host:, Voiceover:, etc.)
        text = re.sub(r'^(Narrator|Host|Voiceover|Announcer|Speaker)\s*:', '', text, flags=re.MULTILINE | re.IGNORECASE)

        # Remove timestamps like (0:00-0:15) [0:30] etc
        text = re.sub(r'[\[\(]\d+:\d+[-–]?\d*:?\d*[\]\)]', '', text)

        # Remove standalone section labels that sneak through
        text = re.sub(r'^\s*(Act \d+|Section \d+|Part \d+)\s*:?\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

        # Remove lines that are just formatting artifacts
        text = re.sub(r'^\s*[=\-_]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Clean up quoted narration (remove surrounding quotes from lines)
        text = re.sub(r'^["\u201c](.*)["\u201d]\s*$', r'\1', text, flags=re.MULTILINE)

        # Collapse whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)

        # Remove lines that are just punctuation or numbers
        text = re.sub(r'^\s*[\d\.\,\:\;\!\?\-]+\s*$', '', text, flags=re.MULTILINE)

        return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# TTS ENGINE (Piper — free, local, CPU)
# ══════════════════════════════════════════════════════════════════════════════

class TTSEngine:

    @staticmethod
    def check_piper() -> bool:
        return os.path.exists(Config.PIPER_EXE) and os.path.exists(Config.PIPER_MODEL)

    @staticmethod
    def generate(text: str, output_wav: str) -> bool:
        """
        Generate WAV voiceover using Piper TTS.
        Returns True on success, False on failure.
        """
        if not TTSEngine.check_piper():
            print("  [TTS] Piper not found — using silence placeholder.")
            TTSEngine._write_silence(output_wav, duration_secs=30)
            return False

        # Piper reads from stdin
        cmd = [
            Config.PIPER_EXE,
            "--model", Config.PIPER_MODEL,
            "--output_file", output_wav,
            "--length_scale", "1.05",    # slightly slower = clearer
            "--noise_scale", "0.667",
            "--noise_w", "0.8",
        ]
        try:
            result = subprocess.run(
                cmd,
                input=text.encode('utf-8'),
                capture_output=True,
                timeout=300
            )
            if result.returncode == 0 and os.path.exists(output_wav):
                size = os.path.getsize(output_wav)
                print(f"  [TTS] Generated: {os.path.basename(output_wav)} ({size//1024}KB)")
                return True
            else:
                err = result.stderr.decode('utf-8', errors='replace')[:200]
                print(f"  [TTS] Piper error: {err}")
                TTSEngine._write_silence(output_wav, duration_secs=30)
                return False
        except subprocess.TimeoutExpired:
            print("  [TTS] Timeout — writing silence placeholder.")
            TTSEngine._write_silence(output_wav, duration_secs=30)
            return False
        except Exception as e:
            print(f"  [TTS] Exception: {e}")
            TTSEngine._write_silence(output_wav, duration_secs=30)
            return False

    @staticmethod
    def _write_silence(output_wav: str, duration_secs: int = 30):
        """Write a silent WAV file as a placeholder."""
        if not NUMPY_OK:
            # Write minimal valid WAV header manually
            sample_rate = 22050
            num_samples = sample_rate * duration_secs
            with open(output_wav, 'wb') as f:
                # WAV header
                f.write(b'RIFF')
                f.write((36 + num_samples * 2).to_bytes(4, 'little'))
                f.write(b'WAVEfmt ')
                f.write((16).to_bytes(4, 'little'))
                f.write((1).to_bytes(2, 'little'))   # PCM
                f.write((1).to_bytes(2, 'little'))   # mono
                f.write(sample_rate.to_bytes(4, 'little'))
                f.write((sample_rate * 2).to_bytes(4, 'little'))
                f.write((2).to_bytes(2, 'little'))
                f.write((16).to_bytes(2, 'little'))
                f.write(b'data')
                f.write((num_samples * 2).to_bytes(4, 'little'))
                f.write(b'\x00' * (num_samples * 2))
        else:
            import wave
            sample_rate = 22050
            silence = np.zeros(sample_rate * duration_secs, dtype=np.int16)
            with wave.open(output_wav, 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(silence.tobytes())


# ══════════════════════════════════════════════════════════════════════════════
# VISUAL ENGINE (slide-based + optional Pexels stock footage)
# ══════════════════════════════════════════════════════════════════════════════

class VisualEngine:

    FINANCE_KEYWORDS = {
        "money": ["finance", "business", "money"],
        "savings": ["savings", "bank", "finance"],
        "investment": ["investment", "stocks", "finance"],
        "debt": ["debt", "finance", "credit"],
        "budget": ["budget", "planning", "finance"],
        "salary": ["office", "business", "career"],
        "default": ["finance", "business", "office"],
    }

    @staticmethod
    def get_stock_clips(keyword: str, section_type: str, count: int = 3) -> list:
        """Fetch free stock video clips from Pexels."""
        if not Config.PEXELS_API_KEY:
            return []

        search_terms = VisualEngine.FINANCE_KEYWORDS.get(
            keyword.lower(),
            VisualEngine.FINANCE_KEYWORDS["default"]
        )

        clips = []
        for term in search_terms[:2]:
            try:
                resp = requests.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": Config.PEXELS_API_KEY},
                    params={"query": term, "per_page": count, "orientation": "landscape"},
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for video in data.get("videos", [])[:count]:
                        # Get HD file
                        files = video.get("video_files", [])
                        hd = next((f for f in files if f.get("quality") == "hd"), None)
                        if hd:
                            clips.append(hd["link"])
            except Exception:
                pass
        return clips

    @staticmethod
    def create_slide(
        text: str,
        section_type: str,
        title: str,
        duration: float,
        size=(1920, 1080),
        accent_idx: int = 0
    ) -> str:
        """
        Create a single PNG slide with dark background + text overlay.
        Returns path to PNG.
        Returns None if PIL not available.
        """
        if not PIL_OK or not NUMPY_OK:
            return None

        bg_hex = Config.SECTION_COLORS.get(section_type, Config.SECTION_COLORS["default"])
        accent_hex = Config.ACCENT_COLORS[accent_idx % len(Config.ACCENT_COLORS)]

        # Convert hex to RGB
        bg_rgb = tuple(int(bg_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        accent_rgb = tuple(int(accent_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        img = Image.new('RGB', size, bg_rgb)
        draw = ImageDraw.Draw(img)

        # Try to use a nice font, fall back to default
        try:
            # Windows system fonts
            font_paths = [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\arial.ttf",
                r"C:\Windows\Fonts\calibrib.ttf",
                r"C:\Windows\Fonts\verdanab.ttf",
            ]
            title_font = None
            body_font = None
            for fp in font_paths:
                if os.path.exists(fp):
                    title_font = ImageFont.truetype(fp, 56)
                    body_font = ImageFont.truetype(fp, 38)
                    break
        except Exception:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        if title_font is None:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        # Draw accent bar at top
        draw.rectangle([(0, 0), (size[0], 8)], fill=accent_rgb)

        # Draw title in accent color
        title_short = title[:60] + ("..." if len(title) > 60 else "")
        draw.text((80, 60), title_short, font=title_font, fill=accent_rgb)

        # Draw section label
        section_label = section_type.upper().replace("ACT", "PART ")
        draw.text((80, 130), section_label, font=body_font, fill=(120, 120, 120))

        # Draw body text (wrapped)
        body_lines = textwrap.wrap(text[:400], width=55)[:10]
        y_text = 220
        for line in body_lines:
            draw.text((80, y_text), line, font=body_font, fill=(220, 220, 220))
            y_text += 55

        # Draw bottom accent bar
        draw.rectangle([(0, size[1]-8), (size[0], size[1])], fill=accent_rgb)

        # Save
        os.makedirs(Config.ASSETS_DIR, exist_ok=True)
        ts = int(time.time() * 1000)
        out_path = os.path.join(Config.ASSETS_DIR, f"slide_{section_type}_{ts}.png")
        img.save(out_path, "PNG")
        return out_path


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO ASSEMBLER
# ══════════════════════════════════════════════════════════════════════════════

class VideoAssembler:

    @staticmethod
    def assemble(
        script_data: dict,
        audio_wav: str,
        output_mp4: str,
        video_num: int = 0
    ) -> bool:
        """
        Assemble final MP4 from audio + slides.
        Returns True on success.
        """
        if not MOVIEPY_OK:
            print("  [VIDEO] MoviePy not installed — skipping assembly.")
            print(f"  [VIDEO] Install with: pip install moviepy")
            return False

        if not PIL_OK:
            print("  [VIDEO] Pillow not installed — skipping assembly.")
            return False

        print(f"  [VIDEO] Loading audio: {os.path.basename(audio_wav)}")

        try:
            audio_clip = AudioFileClip(audio_wav)
            total_duration = audio_clip.duration
            print(f"  [VIDEO] Audio duration: {total_duration:.1f}s")
        except Exception as e:
            print(f"  [VIDEO] Could not load audio: {e}")
            total_duration = 60.0  # fallback

        # Build slide clips for each section
        sections = script_data.get("sections", [{"type": "default", "text": script_data.get("full_narration", "")}])
        title = script_data.get("title", "Personal Finance")

        # Distribute duration evenly across sections
        n_sections = max(1, len(sections))
        section_duration = total_duration / n_sections

        slide_clips = []
        for i, section in enumerate(sections):
            # Create slide PNG
            preview_text = section["text"][:300]
            slide_path = VisualEngine.create_slide(
                text=preview_text,
                section_type=section["type"],
                title=title,
                duration=section_duration,
                accent_idx=video_num + i
            )

            if slide_path and os.path.exists(slide_path):
                clip = ImageClip(slide_path).set_duration(section_duration)

                # Add subtle Ken Burns zoom effect
                try:
                    zoom_factor = 1.0 + (0.03 * (i % 2))  # alternate zoom in/out
                    clip = clip.resize(lambda t: 1 + zoom_factor * t / section_duration)
                    clip = clip.set_position("center")
                except Exception:
                    pass

                slide_clips.append(clip)
            else:
                # Fallback: solid color clip
                color = [15, 23, 42]  # dark blue
                clip = ColorClip(
                    size=(Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT),
                    color=color,
                    duration=section_duration
                )
                slide_clips.append(clip)

        if not slide_clips:
            print("  [VIDEO] No slides generated.")
            return False

        # Concatenate slides
        print(f"  [VIDEO] Concatenating {len(slide_clips)} slides...")
        video = concatenate_videoclips(slide_clips, method="compose")

        # Add captions
        print("  [VIDEO] Adding captions...")
        try:
            video = VideoAssembler._add_captions(video, script_data["full_narration"], total_duration)
        except Exception as e:
            print(f"  [VIDEO] Caption error (non-fatal): {e}")

        # Set audio
        try:
            audio_clips_to_mix = [audio_clip]

            # Add background music if available
            if os.path.exists(Config.MUSIC_FILE):
                try:
                    music = AudioFileClip(Config.MUSIC_FILE)
                    # Loop music to fill video length
                    if music.duration < total_duration:
                        repeats = int(total_duration / music.duration) + 2
                        from moviepy.audio.fx.all import audio_loop
                        music = audio_loop(music, nloops=repeats)
                    music = music.subclip(0, total_duration)
                    music = music.volumex(Config.MUSIC_VOLUME)
                    audio_clips_to_mix.append(music)
                    print(f"  [VIDEO] Background music added at {Config.MUSIC_VOLUME*100:.0f}% volume")
                except Exception as e:
                    print(f"  [VIDEO] Music load failed (non-fatal): {e}")

            if len(audio_clips_to_mix) > 1:
                final_audio = CompositeAudioClip(audio_clips_to_mix)
            else:
                final_audio = audio_clips_to_mix[0]

            video = video.set_audio(final_audio)
        except Exception as e:
            print(f"  [VIDEO] Audio set error: {e}")

        # Trim to audio length
        try:
            video = video.subclip(0, min(total_duration, video.duration))
        except Exception:
            pass

        # Export
        print(f"  [VIDEO] Rendering MP4... (this takes a few minutes)")
        os.makedirs(os.path.dirname(output_mp4), exist_ok=True)

        try:
            video.write_videofile(
                output_mp4,
                fps=Config.VIDEO_FPS,
                codec="libx264",
                audio_codec="aac",
                bitrate=Config.VIDEO_BITRATE,
                preset="medium",
                threads=2,
                logger=None,  # suppress verbose moviepy output
            )
            print(f"  [VIDEO] Saved: {os.path.basename(output_mp4)}")

            # Cleanup temp slides
            for clip in slide_clips:
                try:
                    if hasattr(clip, 'filename') and clip.filename:
                        if os.path.exists(clip.filename):
                            os.remove(clip.filename)
                except Exception:
                    pass

            return True
        except Exception as e:
            print(f"  [VIDEO] Render failed: {e}")
            return False

    @staticmethod
    def _add_captions(video_clip, narration_text: str, total_duration: float):
        """
        Add word-by-word bottom captions.
        Groups words into ~5-word chunks at timed intervals.
        """
        if not narration_text:
            return video_clip

        words = narration_text.split()
        if not words:
            return video_clip

        chunk_size = 5
        chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        chunk_duration = total_duration / max(1, len(chunks))

        caption_clips = []
        for i, chunk in enumerate(chunks):
            try:
                start_t = i * chunk_duration
                # Background box
                txt_clip = (
                    TextClip(
                        chunk,
                        fontsize=Config.CAPTION_FONT_SIZE,
                        color=Config.CAPTION_COLOR,
                        font="Arial-Bold",
                        stroke_color="black",
                        stroke_width=2,
                        method="caption",
                        size=(Config.VIDEO_WIDTH - 200, None),
                        align="center"
                    )
                    .set_position(("center", 0.82), relative=True)
                    .set_start(start_t)
                    .set_duration(chunk_duration)
                )
                caption_clips.append(txt_clip)
            except Exception:
                # TextClip can fail on some systems — skip captions silently
                break

        if caption_clips:
            return CompositeVideoClip([video_clip] + caption_clips)
        return video_clip


# ══════════════════════════════════════════════════════════════════════════════
# METADATA GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class MetadataGenerator:
    """Generates YouTube upload metadata for each video."""

    HASHTAGS = ["#personalfinance", "#moneytips", "#financialfreedom",
                "#budgeting", "#investing", "#savemoney"]

    @staticmethod
    def generate(script_data: dict, video_num: int) -> dict:
        title = script_data["title"]
        section_texts = [s["text"][:100] for s in script_data.get("sections", [])]
        first_200 = script_data["full_narration"][:200]

        # Build description
        description = f"""{first_200}...

In this video we cover:
{chr(10).join(f"• {s[:80]}" for s in section_texts[:5])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Subscribe for weekly personal finance tips
👍 Like if this helped you
💬 Comment your biggest money challenge below
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DISCLAIMER: This video is for educational purposes only and does not constitute financial advice. Please consult a qualified financial advisor before making investment decisions.

{' '.join(MetadataGenerator.HASHTAGS)}
"""

        tags = [
            title,
            "personal finance",
            "money tips",
            "financial freedom",
            "budgeting tips",
            "how to save money",
            "investing for beginners",
            "financial advice",
            "money management",
            "wealth building",
            "passive income",
            "financial independence",
            "money habits",
            "personal finance 2026",
        ]

        return {
            "video_number": video_num,
            "title": title,
            "description": description,
            "tags": tags,
            "category": "27",          # Education
            "defaultLanguage": "en",
            "privacyStatus": "private", # Set to public after review
        }


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY CHECKER & INSTALLER
# ══════════════════════════════════════════════════════════════════════════════

def check_dependencies() -> dict:
    status = {
        "moviepy": MOVIEPY_OK,
        "pillow": PIL_OK,
        "numpy": NUMPY_OK,
        "piper": os.path.exists(Config.PIPER_EXE),
        "piper_model": os.path.exists(Config.PIPER_MODEL),
    }

    print("\n── Dependency Check ──────────────────────────────────")
    for dep, ok in status.items():
        icon = "✓" if ok else "✗"
        print(f"  {icon} {dep}")

    missing_pip = []
    if not MOVIEPY_OK: missing_pip.append("moviepy")
    if not PIL_OK:     missing_pip.append("pillow")
    if not NUMPY_OK:   missing_pip.append("numpy")

    if missing_pip:
        print(f"\n  Install missing packages:")
        print(f"  pip install {' '.join(missing_pip)}")

    if not status["piper"]:
        print(f"\n  Piper TTS not found at: {Config.PIPER_EXE}")
        print(f"  Download: https://github.com/rhasspy/piper/releases")
        print(f"  Place piper.exe in: {os.path.dirname(Config.PIPER_EXE)}")

    if not status["piper_model"]:
        print(f"\n  Piper voice model not found at: {Config.PIPER_MODEL}")
        print(f"  Download en_US-lessac-high.onnx from:")
        print(f"  https://github.com/rhasspy/piper/releases")

    print("──────────────────────────────────────────────────────\n")
    return status


# ══════════════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER
# ══════════════════════════════════════════════════════════════════════════════

class ProgressTracker:
    def __init__(self):
        os.makedirs(Config.LOGS_DIR, exist_ok=True)
        self.log_path = os.path.join(Config.LOGS_DIR, "video_pipeline_progress.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"completed": [], "failed": [], "skipped": []}

    def save(self):
        with open(self.log_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def mark_done(self, video_id):
        if video_id not in self.data["completed"]:
            self.data["completed"].append(video_id)
        self.save()

    def mark_failed(self, video_id, reason):
        self.data["failed"].append({"id": video_id, "reason": reason, "time": datetime.now().isoformat()})
        self.save()

    def is_done(self, video_id):
        return video_id in self.data["completed"]

    def summary(self):
        return (f"Done: {len(self.data['completed'])} | "
                f"Failed: {len(self.data['failed'])} | "
                f"Total tracked: {len(self.data['completed']) + len(self.data['failed'])}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def get_script_files() -> list:
    """Find all script .txt files."""
    scripts_dir = Config.SCRIPTS_DIR
    if not os.path.exists(scripts_dir):
        # Try the uploads location as fallback
        alt = r"C:\money-machine\youtube"
        if os.path.exists(alt):
            scripts_dir = alt

    if not os.path.exists(scripts_dir):
        print(f"Scripts directory not found: {scripts_dir}")
        return []

    files = sorted(Path(scripts_dir).glob("*.txt"))
    return [str(f) for f in files]


def run_pipeline(script_files: list, force_redo: bool = False):
    tracker = ProgressTracker()

    print(f"\nFound {len(script_files)} script files.")
    print(f"Progress: {tracker.summary()}\n")

    total_start = time.time()

    for i, script_path in enumerate(script_files):
        video_id = Path(script_path).stem
        video_num = i + 1

        print(f"\n{'='*60}")
        print(f"[{video_num}/{len(script_files)}] {video_id}")
        print(f"{'='*60}")

        # Skip if already done
        if tracker.is_done(video_id) and not force_redo:
            print(f"  Already completed — skipping. (use --redo to reprocess)")
            continue

        step_start = time.time()

        try:
            # ── STEP 1: Parse script ─────────────────────────────────────
            print("  [1/4] Parsing script...")
            script_data = ScriptParser.parse(script_path)
            print(f"  Title: {script_data['title']}")
            print(f"  Words: {script_data['word_count']} | Sections: {len(script_data['sections'])}")

            if script_data['word_count'] < 50:
                print(f"  WARNING: Very short script ({script_data['word_count']} words) — check file.")

            # ── STEP 2: Generate voiceover ───────────────────────────────
            print("  [2/4] Generating voiceover (TTS)...")
            audio_dir = os.path.join(Config.OUTPUT_DIR, "audio")
            os.makedirs(audio_dir, exist_ok=True)
            audio_wav = os.path.join(audio_dir, f"{video_id}.wav")

            tts_ok = TTSEngine.generate(script_data["full_narration"], audio_wav)
            if not tts_ok:
                print("  WARNING: TTS failed — video will have no narration audio.")

            # ── STEP 3: Assemble video ───────────────────────────────────
            print("  [3/4] Assembling video...")
            safe_title = re.sub(r'[^\w\s-]', '', script_data['title'])[:50]
            safe_title = safe_title.replace(' ', '_')
            output_mp4 = os.path.join(Config.OUTPUT_DIR, f"{video_num:02d}_{safe_title}.mp4")

            video_ok = VideoAssembler.assemble(
                script_data=script_data,
                audio_wav=audio_wav,
                output_mp4=output_mp4,
                video_num=video_num
            )

            # ── STEP 4: Generate metadata ────────────────────────────────
            print("  [4/4] Generating upload metadata...")
            metadata = MetadataGenerator.generate(script_data, video_num)
            meta_path = output_mp4.replace('.mp4', '_metadata.json')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"  Metadata saved: {os.path.basename(meta_path)}")

            # ── Done ─────────────────────────────────────────────────────
            elapsed = round(time.time() - step_start)
            size_mb = os.path.getsize(output_mp4) / (1024*1024) if os.path.exists(output_mp4) else 0
            print(f"\n  ✓ Completed in {elapsed}s | {size_mb:.1f}MB")
            print(f"  Output: {output_mp4}")

            tracker.mark_done(video_id)

        except Exception as e:
            import traceback
            reason = str(e)
            print(f"\n  ✗ FAILED: {reason}")
            print(traceback.format_exc())
            tracker.mark_failed(video_id, reason)
            continue

    # ── Final summary ─────────────────────────────────────────────────────────
    total_elapsed = round(time.time() - total_start)
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  {tracker.summary()}")
    print(f"  Total time: {total_elapsed//3600}h {(total_elapsed%3600)//60}m {total_elapsed%60}s")
    print(f"  Videos: {Config.OUTPUT_DIR}")
    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# SETUP WIZARD — run once to configure everything
# ══════════════════════════════════════════════════════════════════════════════

def setup_wizard():
    print("\n" + "="*60)
    print("  YOUTUBE PIPELINE — FIRST TIME SETUP")
    print("="*60)

    # Create all directories
    dirs = [
        Config.SCRIPTS_DIR,
        Config.OUTPUT_DIR,
        Config.ASSETS_DIR,
        Config.TOOLS_DIR,
        Config.LOGS_DIR,
        os.path.join(Config.OUTPUT_DIR, "audio"),
        os.path.join(Config.TOOLS_DIR, "piper"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"  Created: {d}")

    print("\n  Next steps:")
    print(f"  1. Copy your 20 script .txt files to:")
    print(f"     {Config.SCRIPTS_DIR}")
    print(f"")
    print(f"  2. Download Piper TTS (free):")
    print(f"     https://github.com/rhasspy/piper/releases")
    print(f"     → Download: piper_windows_amd64.zip")
    print(f"     → Extract piper.exe to: {os.path.dirname(Config.PIPER_EXE)}")
    print(f"")
    print(f"  3. Download Piper voice model (free):")
    print(f"     https://github.com/rhasspy/piper/releases → Assets")
    print(f"     → Download: en_US-lessac-high.onnx")
    print(f"     → Place in: {os.path.dirname(Config.PIPER_MODEL)}")
    print(f"")
    print(f"  4. Install Python packages:")
    print(f"     pip install moviepy pillow numpy requests tqdm")
    print(f"")
    print(f"  5. (Optional) Add background music:")
    print(f"     Download royalty-free MP3 from pixabay.com/music")
    print(f"     Save as: {Config.MUSIC_FILE}")
    print(f"")
    print(f"  6. (Optional) Add Pexels API key for stock footage:")
    print(f"     Sign up free at pexels.com/api")
    print(f"     Edit Config.PEXELS_API_KEY in this script")
    print(f"")
    print(f"  Then run: python youtube_video_pipeline.py")
    print("="*60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "="*60)
    print("  YOUTUBE VIDEO PRODUCTION PIPELINE")
    print("  Personal Finance Channel | 20 Videos")
    print("="*60)

    # Parse args
    force_redo = "--redo" in sys.argv
    setup_only = "--setup" in sys.argv

    if setup_only:
        setup_wizard()
        return

    # Check dependencies
    dep_status = check_dependencies()

    # Get script files
    script_files = get_script_files()

    if not script_files:
        print("No script files found.")
        print(f"Place your .txt scripts in: {Config.SCRIPTS_DIR}")
        print("Then run: python youtube_video_pipeline.py")
        print("\nTo run setup wizard: python youtube_video_pipeline.py --setup")
        return

    if not MOVIEPY_OK or not PIL_OK:
        print("\nCannot proceed without moviepy and pillow.")
        print("Install with: pip install moviepy pillow numpy")
        return

    # Confirm
    print(f"Ready to process {len(script_files)} videos.")
    if force_redo:
        print("--redo flag set: will reprocess all videos.")
    ans = input("Start? (y/n): ").strip().lower()
    if ans != 'y':
        print("Cancelled.")
        return

    # Run pipeline
    run_pipeline(script_files, force_redo=force_redo)


if __name__ == "__main__":
    main()
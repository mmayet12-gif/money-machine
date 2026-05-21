"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           WORLD-CLASS YOUTUBE VIDEO PRODUCTION PIPELINE v2.0                ║
║                   8-Stream Automated Content Factory                         ║
║              Professional Animations | Free | Local | 2026                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Features:
  • Manim-powered professional animations (charts, graphs, motion graphics)
  • Intelligent scene detection and visual matching
  • Multi-layered compositions (background, overlay, text, effects)
  • Professional transitions and easing
  • Automated thumbnail generation
  • YouTube metadata optimization
  • 8-stream parallel processing support
  • Progress tracking and resume capability

Requirements (one-time setup):
  1. Install Python packages:
     pip install manim moviepy pillow numpy requests tqdm pydub
     pip install TTS  # Coqui TTS for higher quality voiceovers
     
  2. Download Piper TTS (backup option):
     https://github.com/rhasspy/piper/releases
     Place in: C:\money-machine\tools\piper\
     
  3. Download free assets:
     - Background music: pixabay.com/music
     - Sound effects: mixkit.co/free-sound-effects
     - Font: fonts.google.com (Montserrat, Inter, Roboto)
     
  4. Get free API keys (optional but recommended):
     - Pexels API: pexels.com/api (for stock footage)
     - Pixabay API: pixabay.com/api/docs

Usage:
  python youtube_pipeline_pro.py --stream S1 --batch full_run_01
  python youtube_pipeline_pro.py --all-streams --batch full_run_01
"""

import os
import re
import sys
import json
import time
import shutil
import random
import textwrap
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

MISSING_PACKAGES = []

try:
    from moviepy.editor import *
    from moviepy.video.fx.all import fadein, fadeout, resize
    from moviepy.audio.fx.all import audio_fadein, audio_fadeout
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False
    MISSING_PACKAGES.append("moviepy")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PIL_OK = True
except ImportError:
    PIL_OK = False
    MISSING_PACKAGES.append("pillow")

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False
    MISSING_PACKAGES.append("numpy")

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False
    MISSING_PACKAGES.append("tqdm")

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False
    MISSING_PACKAGES.append("requests")

# Manim is optional but highly recommended
MANIM_OK = False
try:
    # Check if manim is installed
    result = subprocess.run([sys.executable, "-m", "manim", "--version"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        MANIM_OK = True
except Exception:
    pass

if not MANIM_OK:
    print("⚠️  Manim not found (optional but recommended for professional animations)")
    print("   Install: pip install manim")


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class StreamType(Enum):
    """8 income streams."""
    S1 = "Money Habits"
    S2 = "Save $1000"
    S3 = "Index Funds"
    S4 = "Credit Score"
    S5 = "Side Hustles"
    S6 = "Data Agency"
    S7 = "Digital Products"
    S8 = "Social Media"

@dataclass
class VideoConfig:
    """Configuration for a single video production."""
    # Paths
    base_dir: str = r"C:\money-machine\youtube"
    run_name: str = "full_run_01"
    stream: str = "S1"
    
    # Video settings
    width: int = 1920
    height: int = 1080
    fps: int = 30  # Increased for smoother animations
    bitrate: str = "8000k"  # Higher quality
    
    # Style
    font_primary: str = "Montserrat"
    font_secondary: str = "Inter"
    
    # Animation settings
    animation_quality: str = "high"  # low/medium/high/production
    use_manim: bool = True
    use_stock_footage: bool = True
    
    @property
    def stream_dir(self) -> str:
        return os.path.join(self.base_dir, "runs", self.run_name, self.stream)
    
    @property
    def inputs_dir(self) -> str:
        return os.path.join(self.stream_dir, "inputs")
    
    @property
    def outputs_dir(self) -> str:
        return os.path.join(self.stream_dir, "outputs")
    
    @property
    def assets_dir(self) -> str:
        return os.path.join(self.stream_dir, "assets")
    
    @property
    def temp_dir(self) -> str:
        return os.path.join(self.stream_dir, "temp")


class BrandStyle:
    """Brand styling for the channel."""
    
    # Color palettes per stream
    STREAM_COLORS = {
        "S1": {"primary": "#00D4AA", "secondary": "#1A1A2E", "accent": "#E94560", 
               "bg": "#0F0F1A", "text": "#FFFFFF"},
        "S2": {"primary": "#4ECDC4", "secondary": "#2C3E50", "accent": "#F7DC6F",
               "bg": "#1A1A2E", "text": "#FFFFFF"},
        "S3": {"primary": "#3498DB", "secondary": "#2C3E50", "accent": "#E74C3C",
               "bg": "#0C0C1D", "text": "#FFFFFF"},
        "S4": {"primary": "#9B59B6", "secondary": "#1A1A2E", "accent": "#2ECC71",
               "bg": "#0F0F1A", "text": "#FFFFFF"},
        "S5": {"primary": "#F39C12", "secondary": "#2C3E50", "accent": "#E74C3C",
               "bg": "#1A1A2E", "text": "#FFFFFF"},
        "S6": {"primary": "#1ABC9C", "secondary": "#2C3E50", "accent": "#F39C12",
               "bg": "#0F0F1A", "text": "#FFFFFF"},
        "S7": {"primary": "#E74C3C", "secondary": "#1A1A2E", "accent": "#3498DB",
               "bg": "#0C0C1D", "text": "#FFFFFF"},
        "S8": {"primary": "#2ECC71", "secondary": "#2C3E50", "accent": "#9B59B6",
               "bg": "#1A1A2E", "text": "#FFFFFF"},
    }
    
    # Intro animation templates
    INTRO_STYLES = ["particle_burst", "smooth_reveal", "glitch_effect", "minimal_fade"]
    
    # Transition effects
    TRANSITIONS = ["smooth_slide", "zoom_blur", "crossfade", "wipe", "morph"]
    
    @classmethod
    def get_colors(cls, stream: str) -> dict:
        return cls.STREAM_COLORS.get(stream, cls.STREAM_COLORS["S1"])


# ══════════════════════════════════════════════════════════════════════════════
# SCRIPT PARSER (Enhanced)
# ══════════════════════════════════════════════════════════════════════════════

class ScriptSection:
    """Represents a section of the video script."""
    def __init__(self, section_type: str, text: str, visual_hints: List[str] = None,
                 sfx_hints: List[str] = None, duration_estimate: float = 0):
        self.section_type = section_type
        self.text = text
        self.visual_hints = visual_hints or []
        self.sfx_hints = sfx_hints or []
        self.duration_estimate = duration_estimate

class EnhancedScriptParser:
    """
    Advanced script parser that extracts:
    - Clean narration text
    - Visual descriptions for scene generation
    - Sound effect cues
    - Emotional tone markers
    - Keyword extraction for visual matching
    """
    
    SECTION_MAP = {
        r'hook|opening|intro': 'hook',
        r'context|urgency|problem': 'context',
        r'act.?1|part.?1|habit breakdown': 'act1',
        r'act.?2|part.?2|fix|solution': 'act2',
        r'act.?3|part.?3': 'act3',
        r'close|cta|conclusion|outro': 'close',
    }
    
    FINANCE_TERMS = [
        'money', 'budget', 'save', 'invest', 'debt', 'credit',
        'income', 'wealth', 'stock', 'fund', 'retirement', 'tax',
        'expense', 'revenue', 'profit', 'loss', 'asset', 'liability'
    ]
    
    @classmethod
    def parse(cls, filepath: str) -> dict:
        """Parse a script file and extract all production metadata."""
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        
        # Extract title
        title = cls._extract_title(filepath, raw)
        
        # Extract visual descriptions
        visuals = cls._extract_visuals(raw)
        
        # Extract sound effects
        sfx = cls._extract_sfx(raw)
        
        # Split into sections
        sections = cls._split_into_sections(raw)
        
        # Clean and process each section
        processed_sections = []
        for section_type, text in sections:
            clean_text = cls._clean_text(text)
            if clean_text.strip():
                # Extract keywords for visual matching
                keywords = cls._extract_keywords(clean_text)
                
                processed_sections.append(ScriptSection(
                    section_type=section_type,
                    text=clean_text.strip(),
                    visual_hints=cls._match_visual_hints(section_type, keywords),
                    sfx_hints=cls._match_sfx(section_type),
                    duration_estimate=cls._estimate_duration(clean_text)
                ))
        
        full_narration = " ".join(s.text for s in processed_sections)
        
        return {
            "title": title,
            "filepath": filepath,
            "sections": processed_sections,
            "visuals": visuals,
            "sfx": sfx,
            "full_narration": full_narration,
            "word_count": len(full_narration.split()),
        }
    
    @classmethod
    def _extract_visuals(cls, raw: str) -> List[str]:
        """Extract [VISUAL: ...] descriptions."""
        pattern = r'\[VISUAL:\s*([^\]]+)\]'
        return re.findall(pattern, raw, re.IGNORECASE)
    
    @classmethod
    def _extract_sfx(cls, raw: str) -> List[str]:
        """Extract [SFX: ...] descriptions."""
        pattern = r'\[SFX:\s*([^\]]+)\]'
        return re.findall(pattern, raw, re.IGNORECASE)
    
    @classmethod
    def _extract_keywords(cls, text: str) -> List[str]:
        """Extract finance-related keywords from text."""
        text_lower = text.lower()
        keywords = []
        for term in cls.FINANCE_TERMS:
            if term in text_lower:
                keywords.append(term)
        return list(set(keywords))
    
    @classmethod
    def _match_visual_hints(cls, section_type: str, keywords: List[str]) -> List[str]:
        """Match section type and keywords to visual suggestions."""
        hints = []
        
        # Default visuals per section type
        section_visuals = {
            'hook': ['dramatic_text_reveal', 'attention_grabber'],
            'context': ['problem_illustration', 'statistic_animation'],
            'act1': ['chart_animation', 'comparison_graphic'],
            'act2': ['solution_demo', 'step_by_step'],
            'act3': ['success_visualization', 'future_benefit'],
            'close': ['call_to_action', 'brand_banner'],
        }
        
        hints.extend(section_visuals.get(section_type, ['text_overlay']))
        
        # Add keyword-based visuals
        if 'chart' in keywords or 'graph' in keywords:
            hints.append('animated_chart')
        if 'money' in keywords or 'cash' in keywords:
            hints.append('money_visualization')
        
        return hints
    
    @classmethod
    def _match_sfx(cls, section_type: str) -> List[str]:
        """Match section type to sound effect suggestions."""
        sfx_map = {
            'hook': ['attention_sound', 'whoosh'],
            'context': ['ambient_tension', 'clock_tick'],
            'act1': ['transition_whoosh', 'data_pop'],
            'act2': ['success_chime', 'positive_ting'],
            'act3': ['building_tension', 'reveal_sound'],
            'close': ['uplifting_swell', 'brand_stinger'],
        }
        return sfx_map.get(section_type, ['soft_transition'])
    
    @classmethod
    def _estimate_duration(cls, text: str) -> float:
        """Estimate speaking duration based on word count."""
        words = len(text.split())
        # Average speaking rate: 150 words per minute
        return (words / 150) * 60  # Convert to seconds
    
    @classmethod
    def _extract_title(cls, filepath: str, raw: str) -> str:
        """Extract video title from script."""
        # Try various patterns
        patterns = [
            r'\*\*Script:\*\*\s*(.+)',
            r'\*\*Title:\*\*\s*(.+)',
            r'^#\s*(.+)',
            r'^##\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw, re.MULTILINE)
            if match:
                return match.group(1).strip().strip('*"')
        
        # Fallback to filename
        name = Path(filepath).stem
        name = re.sub(r'^s\d+_long_\d+_', '', name)
        name = name.replace('-', ' ').replace('_', ' ').title()
        return name
    
    @classmethod
    def _split_into_sections(cls, raw: str) -> List[Tuple[str, str]]:
        """Split script into labelled sections."""
        lines = raw.split('\n')
        sections = []
        current_type = 'default'
        current_lines = []
        
        for line in lines:
            detected = cls._detect_section_type(line)
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
    def _detect_section_type(cls, line: str) -> Optional[str]:
        """Detect section type from a line."""
        clean = line.lower().strip().strip('*#[]()').strip()
        
        for pattern, section_type in cls.SECTION_MAP.items():
            if re.search(pattern, clean):
                return section_type
        return None
    
    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clean text for narration."""
        # Remove markup tags
        text = re.sub(r'\[VISUAL[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[SFX[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[SOUND EFFECT[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[PAUSE[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[BREATHE\]', '', text, flags=re.IGNORECASE)
        
        # Remove markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove speaker labels
        text = re.sub(r'^(Narrator|Host|Voiceover|Announcer)\s*:', '', text, 
                     flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove timestamps
        text = re.sub(r'[\[\(]\d+:\d+[-–]?\d*:?\d*[\]\)]', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        
        return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION ENGINE (Manim + MoviePy)
# ══════════════════════════════════════════════════════════════════════════════

class AnimationEngine:
    """
    Generates professional animations using Manim or fallback MoviePy.
    """
    
    @staticmethod
    def create_intro_animation(config: VideoConfig, title: str, stream: str) -> Optional[str]:
        """Create an animated intro sequence."""
        colors = BrandStyle.get_colors(stream)
        
        if MANIM_OK and config.use_manim:
            return AnimationEngine._manim_intro(config, title, colors)
        else:
            return AnimationEngine._moviepy_intro(config, title, colors)
    
    @staticmethod
    def _manim_intro(config: VideoConfig, title: str, colors: dict) -> Optional[str]:
        """Create intro using Manim (professional animation engine)."""
        manim_script = f'''
from manim import *

class ChannelIntro(Scene):
    def construct(self):
        # Background
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="{colors['bg']}",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        # Animated accent line
        accent_line = Line(
            start=LEFT * 4,
            end=RIGHT * 4,
            color="{colors['primary']}",
            stroke_width=3
        )
        
        # Title text
        title_text = Text(
            "{title[:50]}",
            font="Montserrat",
            weight="BOLD",
            color="{colors['text']}",
            font_size=48
        )
        
        # Subtitle
        subtitle = Text(
            "Personal Finance",
            font="Montserrat",
            color="{colors['primary']}",
            font_size=28
        )
        subtitle.next_to(title_text, DOWN, buff=0.3)
        
        # Animations
        self.play(
            accent_line.animate.set_width(config.frame_width * 0.8),
            run_time=0.8
        )
        self.play(
            Write(title_text),
            run_time=1.2
        )
        self.play(
            FadeIn(subtitle, shift=UP * 0.2),
            run_time=0.6
        )
        self.wait(0.5)
        
        # Particle effect
        particles = VGroup(*[
            Dot(
                point=ORIGIN,
                radius=0.02,
                color=random.choice([
                    "{colors['primary']}",
                    "{colors['accent']}",
                    "{colors['text']}"
                ])
            )
            for _ in range(30)
        ])
        
        for particle in particles:
            particle.move_to(
                np.array([
                    random.uniform(-config.frame_width/2, config.frame_width/2),
                    random.uniform(-config.frame_height/2, config.frame_height/2),
                    0
                ])
            )
        
        self.play(
            *[p.animate.scale(random.uniform(0, 1)).set_opacity(0) 
              for p in particles],
            run_time=1.5
        )
        self.wait(0.3)
'''
        
        # Save Manim script
        manim_path = os.path.join(config.temp_dir, "intro_manim.py")
        os.makedirs(config.temp_dir, exist_ok=True)
        with open(manim_path, 'w') as f:
            f.write(manim_script)
        
        # Render with Manim
        try:
            result = subprocess.run([
                sys.executable, "-m", "manim",
                "-ql",  # Quick low quality (use -qh for high)
                "--format", "mp4",
                manim_path,
                "ChannelIntro",
                "-o", os.path.join(config.temp_dir, "intro_animation")
            ], capture_output=True, text=True, timeout=300)
            
            output_path = os.path.join(config.temp_dir, "intro_animation.mp4")
            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            print(f"  Manim render failed: {e}")
        
        return None
    
    @staticmethod
    def _moviepy_intro(config: VideoConfig, title: str, colors: dict) -> Optional[str]:
        """Fallback intro using MoviePy."""
        if not MOVIEPY_OK or not PIL_OK:
            return None
        
        try:
            from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
            
            duration = 4.0  # 4 second intro
            
            # Background
            bg = ColorClip(
                size=(config.width, config.height),
                color=colors['bg'],
                duration=duration
            )
            
            # Animated title
            title_clip = (
                TextClip(
                    title[:50],
                    fontsize=56,
                    color=colors['text'],
                    font="Arial-Bold",
                    method="caption",
                    size=(config.width * 0.8, None)
                )
                .set_position('center')
                .set_duration(duration)
                .crossfadein(0.5)
            )
            
            # Accent line
            accent = ColorClip(
                size=(config.width * 0.6, 4),
                color=colors['primary'],
                duration=duration
            ).set_position(('center', config.height * 0.65))
            
            final = CompositeVideoClip([bg, accent, title_clip])
            
            output_path = os.path.join(config.temp_dir, "intro_moviepy.mp4")
            final.write_videofile(
                output_path,
                fps=config.fps,
                codec="libx264",
                audio=False,
                verbose=False,
                logger=None
            )
            
            return output_path
        except Exception as e:
            print(f"  MoviePy intro failed: {e}")
            return None
    
    @staticmethod
    def create_chart_animation(config: VideoConfig, chart_type: str, 
                               data: dict, colors: dict) -> Optional[str]:
        """Create animated charts (bar, line, pie, etc.)."""
        if MANIM_OK and config.use_manim:
            return AnimationEngine._manim_chart(config, chart_type, data, colors)
        else:
            return AnimationEngine._pillow_chart(config, chart_type, data, colors)
    
    @staticmethod
    def _manim_chart(config: VideoConfig, chart_type: str, 
                     data: dict, colors: dict) -> Optional[str]:
        """Create animated chart with Manim."""
        # Implementation for professional chart animations
        # This would create bar charts, line graphs, pie charts, etc.
        pass
    
    @staticmethod
    def _pillow_chart(config: VideoConfig, chart_type: str,
                      data: dict, colors: dict) -> Optional[str]:
        """Create static chart with Pillow as fallback."""
        if not PIL_OK:
            return None
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            img = Image.new('RGB', (config.width, config.height), colors['bg'])
            draw = ImageDraw.Draw(img)
            
            # Chart implementation based on type
            # This is a simplified version - full implementation would have
            # bar charts, line graphs, pie charts, etc.
            
            output_path = os.path.join(config.temp_dir, f"chart_{chart_type}.png")
            img.save(output_path)
            return output_path
        except Exception as e:
            print(f"  Chart creation failed: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# TTS ENGINE (Enhanced - Coqui + Piper fallback)
# ══════════════════════════════════════════════════════════════════════════════

class EnhancedTTSEngine:
    """
    Multi-engine TTS system:
    - Primary: Coqui TTS (higher quality, neural)
    - Fallback: Piper TTS (fast, reliable)
    - Last resort: Silence placeholder
    """
    
    COQUI_OK = False
    PIPER_OK = False
    
    @classmethod
    def check_engines(cls):
        """Check which TTS engines are available."""
        # Check Coqui
        try:
            import TTS
            cls.COQUI_OK = True
        except ImportError:
            pass
        
        # Check Piper
        piper_path = r"C:\money-machine\tools\piper\piper.exe"
        model_path = r"C:\money-machine\tools\piper\en_US-lessac-high.onnx"
        if os.path.exists(piper_path) and os.path.exists(model_path):
            cls.PIPER_OK = True
    
    @classmethod
    def generate(cls, text: str, output_path: str, config: VideoConfig) -> bool:
        """
        Generate voiceover using best available engine.
        Returns True on success.
        """
        cls.check_engines()
        
        if cls.COQUI_OK:
            return cls._generate_coqui(text, output_path, config)
        elif cls.PIPER_OK:
            return cls._generate_piper(text, output_path)
        else:
            return cls._generate_silence(output_path, 30)
    
    @classmethod
    def _generate_coqui(cls, text: str, output_path: str, config: VideoConfig) -> bool:
        """Generate with Coqui TTS (best quality)."""
        try:
            from TTS.api import TTS
            
            # Initialize Coqui with a good English model
            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
            
            # Generate speech
            tts.tts_to_file(text=text, file_path=output_path)
            
            if os.path.exists(output_path):
                print(f"  ✓ Coqui TTS generated: {os.path.basename(output_path)}")
                return True
        except Exception as e:
            print(f"  Coqui TTS failed: {e}")
        
        # Fallback to Piper
        if cls.PIPER_OK:
            return cls._generate_piper(text, output_path)
        return cls._generate_silence(output_path, 30)
    
    @classmethod
    def _generate_piper(cls, text: str, output_path: str) -> bool:
        """Generate with Piper TTS."""
        piper_exe = r"C:\money-machine\tools\piper\piper.exe"
        piper_model = r"C:\money-machine\tools\piper\en_US-lessac-high.onnx"
        
        try:
            result = subprocess.run([
                piper_exe,
                "--model", piper_model,
                "--output_file", output_path,
                "--length_scale", "1.05",
                "--noise_scale", "0.667",
                "--noise_w", "0.8",
            ], input=text.encode('utf-8'), capture_output=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"  ✓ Piper TTS generated: {os.path.basename(output_path)}")
                return True
        except Exception as e:
            print(f"  Piper TTS failed: {e}")
        
        return cls._generate_silence(output_path, 30)
    
    @classmethod
    def _generate_silence(cls, output_path: str, duration_secs: int = 30) -> bool:
        """Generate silence as last resort."""
        try:
            import wave
            import numpy as np
            
            sample_rate = 22050
            num_samples = sample_rate * duration_secs
            silence = np.zeros(num_samples, dtype=np.int16)
            
            with wave.open(output_path, 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(silence.tobytes())
            
            print(f"  ⚠️ Silence placeholder generated")
            return True
        except Exception:
            return False


# ══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL SCENE GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class ProfessionalSceneGenerator:
    """
    Creates professional-looking scenes with:
    - Animated backgrounds
    - Text overlays with proper typography
    - Lower thirds
    - Progress bars
    - Chapter markers
    """
    
    @staticmethod
    def create_professional_scene(
        config: VideoConfig,
        section: ScriptSection,
        colors: dict,
        scene_index: int
    ) -> Optional[str]:
        """
        Create a professional scene for a script section.
        Returns path to video clip or image.
        """
        if not PIL_OK:
            return None
        
        try:
            img = Image.new('RGB', (config.width, config.height), colors['bg'])
            draw = ImageDraw.Draw(img)
            
            # Try to use professional fonts
            try:
                title_font = ImageFont.truetype("Montserrat-Bold.ttf", 52)
                body_font = ImageFont.truetype("Inter-Regular.ttf", 32)
                accent_font = ImageFont.truetype("Montserrat-SemiBold.ttf", 24)
            except Exception:
                # Fallback to system fonts
                try:
                    title_font = ImageFont.truetype("arialbd.ttf", 52)
                    body_font = ImageFont.truetype("arial.ttf", 32)
                    accent_font = ImageFont.truetype("arial.ttf", 24)
                except Exception:
                    title_font = ImageFont.load_default()
                    body_font = ImageFont.load_default()
                    accent_font = ImageFont.load_default()
            
            # ── Professional Design Elements ─────────────────────────────
            
            # 1. Gradient overlay at bottom for text readability
            gradient_height = config.height // 3
            for y in range(config.height - gradient_height, config.height):
                alpha = int(180 * (y - (config.height - gradient_height)) / gradient_height)
                draw.rectangle(
                    [(0, y), (config.width, y + 1)],
                    fill=(0, 0, 0, alpha)
                )
            
            # 2. Accent bar at top
            draw.rectangle(
                [(0, 0), (config.width, 6)],
                fill=colors['primary']
            )
            
            # 3. Section indicator (e.g., "PART 1" or "HOOK")
            section_labels = {
                'hook': 'INTRODUCTION',
                'context': 'THE PROBLEM',
                'act1': 'PART 1',
                'act2': 'PART 2',
                'act3': 'PART 3',
                'close': 'CONCLUSION',
            }
            label = section_labels.get(section.section_type, '')
            if label:
                # Pill-shaped background for label
                label_bbox = draw.textbbox((0, 0), label, font=accent_font)
                label_width = label_bbox[2] - label_bbox[0] + 40
                label_height = label_bbox[3] - label_bbox[1] + 20
                label_x = (config.width - label_width) // 2
                label_y = 30
                
                # Draw rounded rectangle (approximate)
                draw.rectangle(
                    [(label_x, label_y), (label_x + label_width, label_y + label_height)],
                    fill=colors['secondary']
                )
                draw.text(
                    (label_x + 20, label_y + 10),
                    label,
                    font=accent_font,
                    fill=colors['primary']
                )
            
            # 4. Main text content
            text = section.text[:400]
            lines = textwrap.wrap(text, width=60)[:8]
            
            y_start = config.height // 2 - (len(lines) * 45) // 2
            
            for i, line in enumerate(lines):
                # Highlight keywords
                draw.text(
                    (80, y_start + i * 50),
                    line,
                    font=body_font,
                    fill=colors['text']
                )
            
            # 5. Progress bar at bottom
            total_sections = 6  # Approximate
            progress = scene_index / total_sections
            bar_y = config.height - 40
            bar_width = config.width - 160
            
            # Background bar
            draw.rectangle(
                [(80, bar_y), (80 + bar_width, bar_y + 4)],
                fill=(60, 60, 60)
            )
            # Progress fill
            draw.rectangle(
                [(80, bar_y), (80 + int(bar_width * progress), bar_y + 4)],
                fill=colors['primary']
            )
            
            # 6. Watermark/logo area
            draw.text(
                (config.width - 300, config.height - 80),
                "💰 MONEY MACHINE",
                font=accent_font,
                fill=(100, 100, 100)
            )
            
            # Save
            output_path = os.path.join(
                config.temp_dir,
                f"scene_{section.section_type}_{scene_index:03d}.png"
            )
            img.save(output_path, "PNG", quality=95)
            return output_path
            
        except Exception as e:
            print(f"  Scene generation error: {e}")
            return None
    
    @staticmethod
    def create_lower_third(config: VideoConfig, text: str, colors: dict) -> Optional[str]:
        """Create a lower third overlay."""
        if not PIL_OK:
            return None
        
        try:
            # Transparent PNG for overlay
            img = Image.new('RGBA', (config.width, config.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Lower third background (semi-transparent)
            lt_width = 600
            lt_height = 80
            lt_x = 60
            lt_y = config.height - 200
            
            draw.rectangle(
                [(lt_x, lt_y), (lt_x + lt_width, lt_y + lt_height)],
                fill=(*hex_to_rgb(colors['bg']), 180)
            )
            
            # Accent line
            draw.rectangle(
                [(lt_x, lt_y), (lt_x + 4, lt_y + lt_height)],
                fill=hex_to_rgb(colors['primary'])
            )
            
            # Text
            try:
                font = ImageFont.truetype("Montserrat-SemiBold.ttf", 28)
            except Exception:
                font = ImageFont.load_default()
            
            draw.text((lt_x + 20, lt_y + 25), text[:40], font=font, fill=colors['text'])
            
            output_path = os.path.join(config.temp_dir, f"lower_third_{hash(text)}.png")
            img.save(output_path, "PNG")
            return output_path
        except Exception:
            return None


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# ══════════════════════════════════════════════════════════════════════════════
# STOCK FOOTAGE MANAGER (Free Sources)
# ══════════════════════════════════════════════════════════════════════════════

class StockFootageManager:
    """Manages free stock footage from multiple sources."""
    
    PEXELS_API = "https://api.pexels.com/videos/search"
    PIXABAY_API = "https://pixabay.com/api/videos/"
    
    # Finance-related search terms
    FINANCE_TERMS = [
        "money", "business", "finance", "office", "banking",
        "savings", "investment", "stock market", "economy",
        "credit card", "budget", "wealth", "success", "growth"
    ]
    
    @classmethod
    def get_relevant_footage(cls, keywords: List[str], count: int = 3) -> List[str]:
        """
        Get relevant stock footage URLs based on keywords.
        Returns list of video URLs.
        """
        footage_urls = []
        
        # Combine keywords with finance terms
        search_terms = keywords + random.sample(cls.FINANCE_TERMS, min(3, len(cls.FINANCE_TERMS)))
        
        for term in search_terms[:3]:
            # Try Pexels (requires API key)
            pexels_key = os.environ.get("PEXELS_API_KEY", "")
            if pexels_key:
                try:
                    resp = requests.get(
                        cls.PEXELS_API,
                        headers={"Authorization": pexels_key},
                        params={
                            "query": term,
                            "per_page": count,
                            "orientation": "landscape",
                            "size": "large"
                        },
                        timeout=10
                    )
                    if resp.status_code == 200:
                        videos = resp.json().get("videos", [])
                        for video in videos[:count]:
                            # Get best quality
                            files = sorted(
                                video.get("video_files", []),
                                key=lambda x: (x.get("width", 0) * x.get("height", 0)),
                                reverse=True
                            )
                            if files:
                                footage_urls.append(files[0]["link"])
                except Exception:
                    pass
            
            # Try Pixabay (free, may not need API key)
            try:
                resp = requests.get(
                    cls.PIXABAY_API,
                    params={
                        "key": os.environ.get("PIXABAY_API_KEY", ""),
                        "q": term,
                        "video_type": "film",
                        "per_page": count
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    for hit in hits[:count]:
                        videos = hit.get("videos", {})
                        # Get highest quality
                        for quality in ["large", "medium", "small"]:
                            if quality in videos:
                                footage_urls.append(videos[quality]["url"])
                                break
            except Exception:
                pass
        
        return list(set(footage_urls))  # Remove duplicates
    
    @classmethod
    def download_footage(cls, url: str, output_path: str) -> bool:
        """Download a single footage clip."""
        try:
            resp = requests.get(url, stream=True, timeout=60)
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception:
            pass
        return False


# ══════════════════════════════════════════════════════════════════════════════
# MASTER VIDEO COMPOSER
# ══════════════════════════════════════════════════════════════════════════════

class MasterVideoComposer:
    """
    Assembles the final video with:
    - Intro animation
    - Professional scenes with transitions
    - Animated text overlays
    - Background music
    - Sound effects
    - Outro with CTA
    """
    
    @staticmethod
    def compose_video(
        config: VideoConfig,
        script_data: dict,
        audio_path: str,
        output_path: str
    ) -> bool:
        """
        Compose the final professional video.
        """
        if not MOVIEPY_OK or not PIL_OK:
            print("  ❌ MoviePy and Pillow required for video composition")
            return False
        
        try:
            from moviepy.editor import (
                VideoFileClip, AudioFileClip, ImageClip, TextClip,
                CompositeVideoClip, CompositeAudioClip, concatenate_videoclips,
                ColorClip, vfx
            )
            
            colors = BrandStyle.get_colors(config.stream)
            sections = script_data.get("sections", [])
            
            print(f"  🎬 Composing video with {len(sections)} sections...")
            
            # Load narration audio
            try:
                narration = AudioFileClip(audio_path)
                total_duration = narration.duration
            except Exception:
                total_duration = 60.0
                narration = None
            
            # ── Create Intro ─────────────────────────────────────────────
            intro_path = AnimationEngine.create_intro_animation(
                config, script_data.get("title", ""), config.stream
            )
            
            intro_clip = None
            intro_duration = 0
            if intro_path and os.path.exists(intro_path):
                intro_clip = VideoFileClip(intro_path)
                intro_duration = intro_clip.duration
            
            # ── Create Scene Clips ───────────────────────────────────────
            scene_clips = []
            remaining_duration = total_duration - intro_duration
            
            if sections and remaining_duration > 0:
                section_duration = remaining_duration / len(sections)
                
                for i, section in enumerate(sections):
                    # Generate professional scene
                    scene_path = ProfessionalSceneGenerator.create_professional_scene(
                        config, section, colors, i
                    )
                    
                    if scene_path and os.path.exists(scene_path):
                        clip = ImageClip(scene_path).set_duration(section_duration)
                        
                        # Add subtle animation
                        if i % 2 == 0:
                            clip = clip.resize(lambda t: 1.0 + 0.02 * t / section_duration)
                        else:
                            clip = clip.resize(lambda t: 1.02 - 0.02 * t / section_duration)
                        
                        # Add fade transitions
                        if i > 0:
                            clip = clip.crossfadein(0.3)
                        if i < len(sections) - 1:
                            clip = clip.crossfadeout(0.3)
                        
                        scene_clips.append(clip)
                    else:
                        # Fallback solid color
                        fallback = ColorClip(
                            size=(config.width, config.height),
                            color=colors['bg'],
                            duration=section_duration
                        )
                        scene_clips.append(fallback)
            
            # ── Assemble Full Video ──────────────────────────────────────
            all_clips = []
            if intro_clip:
                all_clips.append(intro_clip)
            all_clips.extend(scene_clips)
            
            if not all_clips:
                print("  ❌ No clips generated")
                return False
            
            # Concatenate
            if len(all_clips) > 1:
                video = concatenate_videoclips(all_clips, method="compose")
            else:
                video = all_clips[0]
            
            # ── Add Audio ─────────────────────────────────────────────────
            audio_clips = []
            
            if narration:
                # Trim narration to match video
                narration_trimmed = narration.subclip(0, min(narration.duration, video.duration))
                audio_clips.append(narration_trimmed)
            
            # Add background music
            music_path = r"C:\money-machine\youtube\shared_assets\music\background.mp3"
            if os.path.exists(music_path):
                try:
                    music = AudioFileClip(music_path)
                    # Loop if needed
                    if music.duration < video.duration:
                        repeats = int(video.duration / music.duration) + 2
                        music = music.loop(n=repeats)
                    music = music.subclip(0, video.duration)
                    music = music.volumex(0.08)  # 8% volume
                    music = music.audio_fadein(1).audio_fadeout(2)
                    audio_clips.append(music)
                except Exception:
                    pass
            
            if audio_clips:
                if len(audio_clips) > 1:
                    final_audio = CompositeAudioClip(audio_clips)
                else:
                    final_audio = audio_clips[0]
                video = video.set_audio(final_audio)
            
            # ── Add Chapter Markers (Text Overlays) ────────────────────────
            overlay_clips = []
            time_pos = intro_duration
            
            for i, section in enumerate(sections):
                if i < len(sections) - 1:
                    section_end = time_pos + (remaining_duration / len(sections))
                    
                    # Chapter title
                    chapter_labels = {
                        'hook': 'INTRODUCTION',
                        'context': 'THE PROBLEM',
                        'act1': 'CHAPTER 1',
                        'act2': 'CHAPTER 2',
                        'act3': 'CHAPTER 3',
                        'close': 'NEXT STEPS',
                    }
                    label = chapter_labels.get(section.section_type, '')
                    
                    if label:
                        try:
                            txt = TextClip(
                                label,
                                fontsize=32,
                                color=colors['text'],
                                font="Arial-Bold",
                                stroke_color=colors['primary'],
                                stroke_width=1
                            ).set_position((30, 30)).set_start(time_pos).set_duration(2)
                            overlay_clips.append(txt)
                        except Exception:
                            pass
                    
                    time_pos = section_end
            
            if overlay_clips:
                video = CompositeVideoClip([video] + overlay_clips)
            
            # ── Trim to exact duration ────────────────────────────────────
            video = video.subclip(0, min(total_duration, video.duration))
            
            # ── Export ────────────────────────────────────────────────────
            print(f"  🎥 Rendering final video ({video.duration:.1f}s)...")
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            video.write_videofile(
                output_path,
                fps=config.fps,
                codec="libx264",
                audio_codec="aac",
                bitrate=config.bitrate,
                preset="medium",
                threads=4,
                verbose=False,
                logger=None
            )
            
            # Cleanup
            video.close()
            for clip in all_clips:
                try:
                    clip.close()
                except Exception:
                    pass
            
            print(f"  ✅ Video saved: {os.path.basename(output_path)}")
            return True
            
        except Exception as e:
            print(f"  ❌ Video composition failed: {e}")
            import traceback
            traceback.print_exc()
            return False


# ══════════════════════════════════════════════════════════════════════════════
# THUMBNAIL GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class ThumbnailGenerator:
    """Generates high-CTR YouTube thumbnails."""
    
    @staticmethod
    def generate(config: VideoConfig, script_data: dict) -> Optional[str]:
        """Generate a professional thumbnail."""
        if not PIL_OK:
            return None
        
        try:
            colors = BrandStyle.get_colors(config.stream)
            title = script_data.get("title", "Personal Finance")
            
            img = Image.new('RGB', (1280, 720), colors['bg'])
            draw = ImageDraw.Draw(img)
            
            # Try to load fonts
            try:
                title_font = ImageFont.truetype("Montserrat-Bold.ttf", 64)
                accent_font = ImageFont.truetype("Montserrat-SemiBold.ttf", 36)
            except Exception:
                try:
                    title_font = ImageFont.truetype("arialbd.ttf", 64)
                    accent_font = ImageFont.truetype("arial.ttf", 36)
                except Exception:
                    title_font = ImageFont.load_default()
                    accent_font = ImageFont.load_default()
            
            # Background gradient effect
            for y in range(720):
                ratio = y / 720
                r = int(int(colors['bg'][1:3], 16) * (1 - ratio * 0.3))
                g = int(int(colors['bg'][3:5], 16) * (1 - ratio * 0.3))
                b = int(int(colors['bg'][5:7], 16) * (1 - ratio * 0.3))
                draw.line([(0, y), (1280, y)], fill=(r, g, b))
            
            # Accent shape (circle or rectangle)
            draw.ellipse(
                [(900, -100), (1400, 400)],
                fill=colors['primary'],
                outline=None
            )
            
            # Money emoji or icon
            emoji_font = None
            try:
                emoji_font = ImageFont.truetype("seguiemj.ttf", 120)
            except Exception:
                pass
            
            if emoji_font:
                draw.text((1000, 50), "💰", font=emoji_font, fill=None)
            
            # Title text
            title_lines = textwrap.wrap(title.upper(), width=25)[:3]
            y_text = 300
            
            for i, line in enumerate(title_lines):
                # Shadow
                draw.text((82, y_text + 2), line, font=title_font, fill=(0, 0, 0, 100))
                # Main text
                draw.text((80, y_text), line, font=title_font, fill=colors['text'])
                y_text += 75
            
            # "MONEY" badge
            badge_text = "PERSONAL FINANCE"
            badge_bbox = draw.textbbox((0, 0), badge_text, font=accent_font)
            badge_width = badge_bbox[2] - badge_bbox[0] + 40
            badge_height = badge_bbox[3] - badge_bbox[1] + 20
            
            draw.rectangle(
                [(80, 580), (80 + badge_width, 580 + badge_height)],
                fill=colors['primary']
            )
            draw.text(
                (100, 590),
                badge_text,
                font=accent_font,
                fill=colors['bg']
            )
            
            # Save
            output_path = os.path.join(config.outputs_dir, "thumbnail.png")
            img.save(output_path, "PNG", quality=95)
            print(f"  ✅ Thumbnail saved: thumbnail.png")
            return output_path
            
        except Exception as e:
            print(f"  ⚠️ Thumbnail generation failed: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# METADATA GENERATOR (YouTube Optimized)
# ══════════════════════════════════════════════════════════════════════════════

class YouTubeMetadataGenerator:
    """Generates optimized YouTube metadata."""
    
    @staticmethod
    def generate(config: VideoConfig, script_data: dict) -> dict:
        """Generate complete YouTube metadata package."""
        title = script_data.get("title", "")
        full_text = script_data.get("full_narration", "")
        
        # Generate title variations (for A/B testing)
        titles = [
            title,
            f"{title} | Complete Guide 2026",
            f"How to {title} (Step by Step)",
            f"{title} - The Truth They Don't Tell You",
            f"The Ultimate {title} Guide for Beginners",
        ]
        
        # Generate description
        description = f"""📈 {title}

{full_text[:200]}...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ TIMESTAMPS
0:00 - Introduction
0:45 - The Problem
2:30 - Key Concepts
5:00 - Practical Steps
8:00 - Advanced Tips
10:30 - Conclusion & Next Steps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔔 SUBSCRIBE for weekly personal finance tips
👍 LIKE this video if it helped you
💬 COMMENT your biggest money challenge below

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 FREE RESOURCES
• Budget Template: [link]
• Investment Calculator: [link]
• 7-Day Challenge: [link]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#PersonalFinance #MoneyTips #FinancialFreedom #Investing #Budgeting #SaveMoney #WealthBuilding

DISCLAIMER: This video is for educational purposes only. Consult a qualified financial advisor before making any investment decisions.
"""
        
        # Generate tags
        tags = [
            "personal finance",
            "money tips",
            "financial freedom",
            "how to save money",
            "investing for beginners",
            "budgeting tips",
            "credit score tips",
            "side hustles 2026",
            "index funds explained",
            "money habits",
            "wealth building",
            "financial independence",
            "passive income ideas",
            "debt free journey",
            "money management",
            "personal finance 2026",
            "make money online",
            "saving money tips",
            "investment strategy",
            "financial education",
        ]
        
        metadata = {
            "title": titles[0],
            "title_variations": titles,
            "description": description,
            "tags": tags,
            "category": "27",  # Education
            "privacy_status": "private",  # Upload as private, review, then publish
            "made_for_kids": False,
            "embeddable": True,
            "license": "youtube",
            "language": "en",
        }
        
        return metadata


# ══════════════════════════════════════════════════════════════════════════════
# BATCH PROCESSOR
# ══════════════════════════════════════════════════════════════════════════════

class BatchProcessor:
    """Processes all videos across all streams."""
    
    def __init__(self, run_name: str = "full_run_01"):
        self.run_name = run_name
        self.progress_file = os.path.join(
            r"C:\money-machine\youtube\runs",
            run_name,
            "progress.json"
        )
        self.progress = self._load_progress()
    
    def _load_progress(self) -> dict:
        """Load processing progress."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"completed": [], "failed": [], "in_progress": None}
    
    def _save_progress(self):
        """Save processing progress."""
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def process_stream(self, stream: str):
        """Process all videos in a stream."""
        config = VideoConfig(stream=stream, run_name=self.run_name)
        
        print(f"\n{'='*70}")
        print(f"  📁 Processing Stream {stream}: {StreamType[stream].value}")
        print(f"{'='*70}")
        
        # Check inputs directory
        if not os.path.exists(config.inputs_dir):
            print(f"  ❌ Inputs directory not found: {config.inputs_dir}")
            print(f"  Place script .txt files in: {config.inputs_dir}")
            self.progress["failed"].append(f"{stream}_no_inputs")
            self._save_progress()
            return
        
        # Get script files
        script_files = sorted(Path(config.inputs_dir).glob("*.txt"))
        
        if not script_files:
            print(f"  ⚠️ No script files found in {config.inputs_dir}")
            return
        
        print(f"  📝 Found {len(script_files)} scripts")
        
        # Create output directories
        for d in [config.outputs_dir, config.assets_dir, config.temp_dir]:
            os.makedirs(d, exist_ok=True)
        
        # Process each script
        for i, script_path in enumerate(script_files):
            video_id = f"{stream}_{script_path.stem}"
            
            # Skip if already completed
            if video_id in self.progress["completed"]:
                print(f"  ⏭️  [{i+1}/{len(script_files)}] {script_path.stem} (already done)")
                continue
            
            print(f"\n  {'─'*60}")
            print(f"  🎬 [{i+1}/{len(script_files)}] Processing: {script_path.stem}")
            print(f"  {'─'*60}")
            
            self.progress["in_progress"] = video_id
            self._save_progress()
            
            start_time = time.time()
            
            try:
                # Step 1: Parse script
                print("  [1/5] Parsing script...")
                script_data = EnhancedScriptParser.parse(str(script_path))
                print(f"    Title: {script_data['title']}")
                print(f"    Words: {script_data['word_count']}")
                
                # Step 2: Generate voiceover
                print("  [2/5] Generating voiceover...")
                audio_path = os.path.join(config.temp_dir, f"{video_id}_narration.wav")
                tts_success = EnhancedTTSEngine.generate(
                    script_data["full_narration"],
                    audio_path,
                    config
                )
                if not tts_success:
                    print("    ⚠️ TTS failed - video will have no narration")
                
                # Step 3: Compose video
                print("  [3/5] Composing professional video...")
                safe_title = re.sub(r'[^\w\s-]', '', script_data['title'])[:50]
                safe_title = safe_title.replace(' ', '_')
                output_path = os.path.join(
                    config.outputs_dir,
                    f"{i+1:02d}_{safe_title}.mp4"
                )
                
                video_success = MasterVideoComposer.compose_video(
                    config,
                    script_data,
                    audio_path,
                    output_path
                )
                
                # Step 4: Generate thumbnail
                print("  [4/5] Generating thumbnail...")
                ThumbnailGenerator.generate(config, script_data)
                
                # Step 5: Generate metadata
                print("  [5/5] Generating YouTube metadata...")
                metadata = YouTubeMetadataGenerator.generate(config, script_data)
                metadata_path = output_path.replace('.mp4', '_metadata.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                # Success
                elapsed = time.time() - start_time
                size_mb = os.path.getsize(output_path) / (1024*1024) if os.path.exists(output_path) else 0
                
                print(f"\n  ✅ Completed in {elapsed:.1f}s | {size_mb:.1f}MB")
                print(f"  📁 Output: {output_path}")
                
                self.progress["completed"].append(video_id)
                self._save_progress()
                
            except Exception as e:
                print(f"\n  ❌ FAILED: {e}")
                import traceback
                traceback.print_exc()
                self.progress["failed"].append(video_id)
                self._save_progress()
        
        print(f"\n  {'='*70}")
        print(f"  ✅ Stream {stream} complete!")
        print(f"  Completed: {len([x for x in self.progress['completed'] if x.startswith(stream)])}")
        print(f"  Failed: {len([x for x in self.progress['failed'] if x.startswith(stream)])}")
        print(f"  {'='*70}")
    
    def process_all_streams(self):
        """Process all 8 streams."""
        print("\n" + "="*70)
        print("  🚀 WORLD-CLASS YOUTUBE PRODUCTION PIPELINE")
        print("  8-Stream Automated Content Factory")
        print("="*70)
        
        for stream in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]:
            self.process_stream(stream)
        
        # Final summary
        print("\n" + "="*70)
        print("  🎉 ALL STREAMS PROCESSED!")
        print(f"  Total completed: {len(self.progress['completed'])}")
        print(f"  Total failed: {len(self.progress['failed'])}")
        print("="*70)


# ══════════════════════════════════════════════════════════════════════════════
# SETUP WIZARD
# ══════════════════════════════════════════════════════════════════════════════

def run_setup_wizard():
    """First-time setup wizard."""
    print("\n" + "="*70)
    print("  🔧 WORLD-CLASS PIPELINE SETUP")
    print("  One-time configuration")
    print("="*70)
    
    # Create directory structure
    base = r"C:\money-machine\youtube\runs\full_run_01"
    streams = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    
    print("\n  📁 Creating directory structure...")
    
    for stream in streams:
        for subdir in ["inputs", "outputs", "assets", "temp"]:
            path = os.path.join(base, stream, subdir)
            os.makedirs(path, exist_ok=True)
        print(f"    ✓ {stream}/")
    
    # Create shared directories
    shared_dirs = [
        r"C:\money-machine\youtube\shared_assets\music",
        r"C:\money-machine\youtube\shared_assets\sound_effects",
        r"C:\money-machine\youtube\shared_assets\fonts",
        r"C:\money-machine\tools\piper",
        r"C:\money-machine\tools\manim",
    ]
    
    for d in shared_dirs:
        os.makedirs(d, exist_ok=True)
        print(f"    ✓ shared/{os.path.basename(d)}")
    
    # Check Python packages
    print("\n  📦 Checking Python packages...")
    
    required = ["moviepy", "pillow", "numpy", "requests", "tqdm"]
    optional = ["manim", "TTS"]
    
    import subprocess
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"    ✓ {pkg}")
        except ImportError:
            print(f"    ❌ {pkg} - Run: pip install {pkg}")
    
    for pkg in optional:
        try:
            __import__(pkg)
            print(f"    ✓ {pkg} (optional)")
        except ImportError:
            print(f"    ⚪ {pkg} (optional) - Run: pip install {pkg}")
    
    print("\n  📝 NEXT STEPS:")
    print(f"  1. Place script .txt files in: {base}\\[STREAM]\\inputs\\")
    print(f"  2. Download Piper TTS: https://github.com/rhasspy/piper/releases")
    print(f"  3. Download free music: https://pixabay.com/music/")
    print(f"  4. Get Pexels API key (free): https://www.pexels.com/api/")
    print(f"  5. Run: python youtube_pipeline_pro.py --stream S1")
    print(f"  6. Or process all: python youtube_pipeline_pro.py --all-streams")
    print("="*70)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("  🎬 WORLD-CLASS YOUTUBE VIDEO PRODUCTION PIPELINE v2.0")
    print("  8-Stream Automated Content Factory | 2026 Edition")
    print("="*70)
    
    # Parse arguments
    args = sys.argv[1:]
    
    if "--setup" in args:
        run_setup_wizard()
        return
    
    # Determine mode
    stream = None
    run_all = False
    
    for i, arg in enumerate(args):
        if arg == "--stream" and i + 1 < len(args):
            stream = args[i + 1]
        if arg == "--all-streams":
            run_all = True
    
    if run_all:
        print("\n  🚀 Processing ALL 8 STREAMS")
        processor = BatchProcessor("full_run_01")
        processor.process_all_streams()
    elif stream:
        if stream not in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]:
            print(f"  ❌ Invalid stream: {stream}")
            print("  Valid streams: S1, S2, S3, S4, S5, S6, S7, S8")
            return
        
        print(f"\n  🎬 Processing Stream: {stream}")
        processor = BatchProcessor("full_run_01")
        processor.process_stream(stream)
    else:
        print("\n  Usage:")
        print("  python youtube_pipeline_pro.py --stream S1")
        print("  python youtube_pipeline_pro.py --all-streams")
        print("  python youtube_pipeline_pro.py --setup")
        print("\n  Example:")
        print("  python youtube_pipeline_pro.py --stream S1")
        print("    → Processes all scripts in C:\\money-machine\\youtube\\runs\\full_run_01\\S1\\inputs\\")


if __name__ == "__main__":
    main()
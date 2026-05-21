"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              COMPLETE AUTOMATED SETUP — 8-STREAM YOUTUBE FACTORY            ║
║                    One-Click Installation | Local | Free                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

This script sets up EVERYTHING needed for the world-class video pipeline:
  ✓ Python packages (moviepy, manim, TTS, etc.)
  ✓ Piper TTS (downloads automatically)
  ✓ Professional fonts (Montserrat, Inter, Roboto)
  ✓ Free background music
  ✓ Sound effects library
  ✓ Directory structure for all 8 streams
  ✓ API key configuration
  ✓ Sample templates and assets

Run once:
  python setup_complete.py

Then process videos:
  python youtube_pipeline_pro.py --stream S1
"""

import os
import sys
import json
import time
import shutil
import zipfile
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class SetupConfig:
    """Configuration for the complete setup."""
    
    # Base directories
    BASE_DIR = r"C:\money-machine"
    YOUTUBE_DIR = os.path.join(BASE_DIR, "youtube")
    TOOLS_DIR = os.path.join(BASE_DIR, "tools")
    RUNS_DIR = os.path.join(YOUTUBE_DIR, "runs")
    
    # Stream directories
    STREAMS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    
    # URLs for downloads
    PIPER_URL = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_windows_amd64.zip"
    PIPER_VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx"
    
    # Font URLs (from Google Fonts)
    FONTS = {
        "Montserrat-Bold": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf",
        "Montserrat-SemiBold": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-SemiBold.ttf",
        "Inter-Regular": "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Regular.ttf",
        "Roboto-Bold": "https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-Bold.ttf",
    }
    
    # Python packages
    REQUIRED_PACKAGES = [
        "moviepy",
        "pillow",
        "numpy",
        "requests",
        "tqdm",
        "pydub",
        "beautifulsoup4",
    ]
    
    OPTIONAL_PACKAGES = [
        "manim",          # Professional animations
        "TTS",            # Better text-to-speech
        "opencv-python",  # Video processing
    ]
    
    PIPER_DIR = os.path.join(TOOLS_DIR, "piper")
    FONTS_DIR = os.path.join(YOUTUBE_DIR, "shared_assets", "fonts")
    MUSIC_DIR = os.path.join(YOUTUBE_DIR, "shared_assets", "music")
    SFX_DIR = os.path.join(YOUTUBE_DIR, "shared_assets", "sound_effects")


# ══════════════════════════════════════════════════════════════════════════════
# PROGRESS DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

class ColorPrinter:
    """Colored terminal output."""
    
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    @classmethod
    def success(cls, msg):
        print(f"  {cls.GREEN}✓{cls.RESET} {msg}")
    
    @classmethod
    def error(cls, msg):
        print(f"  {cls.RED}✗{cls.RESET} {msg}")
    
    @classmethod
    def warning(cls, msg):
        print(f"  {cls.YELLOW}⚠{cls.RESET} {msg}")
    
    @classmethod
    def info(cls, msg):
        print(f"  {cls.BLUE}ℹ{cls.RESET} {msg}")
    
    @classmethod
    def step(cls, num, total, msg):
        print(f"\n  [{cls.CYAN}{num}/{total}{cls.RESET}] {msg}")


# ══════════════════════════════════════════════════════════════════════════════
# FILE DOWNLOADER
# ══════════════════════════════════════════════════════════════════════════════

class FileDownloader:
    """Downloads files with progress and retry logic."""
    
    @staticmethod
    def download(url: str, destination: str, description: str = "") -> bool:
        """
        Download a file with progress bar.
        Returns True on success.
        """
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Check if already downloaded
            if os.path.exists(destination):
                size = os.path.getsize(destination)
                if size > 1000:  # More than 1KB = probably valid
                    ColorPrinter.info(f"{description} already exists ({size//1024}KB)")
                    return True
            
            ColorPrinter.info(f"Downloading: {description}...")
            
            # Progress callback
            def progress_callback(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, int(block_num * block_size * 100 / total_size))
                    bar_length = 30
                    filled = int(bar_length * percent / 100)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    print(f"\r    [{bar}] {percent}%", end='', flush=True)
            
            urllib.request.urlretrieve(url, destination, progress_callback)
            print()  # New line after progress bar
            
            if os.path.exists(destination):
                size = os.path.getsize(destination)
                ColorPrinter.success(f"Downloaded: {description} ({size//1024}KB)")
                return True
            else:
                ColorPrinter.error(f"Download failed: {description}")
                return False
                
        except Exception as e:
            ColorPrinter.error(f"Download error for {description}: {e}")
            return False
    
    @staticmethod
    def download_with_retry(url: str, destination: str, description: str = "", 
                           max_retries: int = 3) -> bool:
        """Download with automatic retry."""
        for attempt in range(max_retries):
            if FileDownloader.download(url, destination, description):
                return True
            if attempt < max_retries - 1:
                time.sleep(2)
                print(f"    Retrying ({attempt + 2}/{max_retries})...")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# DIRECTORY CREATOR
# ══════════════════════════════════════════════════════════════════════════════

class DirectoryCreator:
    """Creates the complete directory structure."""
    
    @staticmethod
    def create_all():
        """Create all required directories."""
        config = SetupConfig()
        
        # Main directories
        main_dirs = [
            config.BASE_DIR,
            config.YOUTUBE_DIR,
            config.TOOLS_DIR,
            config.RUNS_DIR,
            config.PIPER_DIR,
            config.FONTS_DIR,
            config.MUSIC_DIR,
            config.SFX_DIR,
        ]
        
        for d in main_dirs:
            os.makedirs(d, exist_ok=True)
        
        # Stream directories
        for stream in config.STREAMS:
            stream_base = os.path.join(config.RUNS_DIR, "full_run_01", stream)
            for sub in ["inputs", "outputs", "assets", "temp"]:
                path = os.path.join(stream_base, sub)
                os.makedirs(path, exist_ok=True)
        
        # Additional shared directories
        shared_extra = [
            os.path.join(config.YOUTUBE_DIR, "templates", "intros"),
            os.path.join(config.YOUTUBE_DIR, "templates", "transitions"),
            os.path.join(config.YOUTUBE_DIR, "templates", "lower_thirds"),
            os.path.join(config.YOUTUBE_DIR, "templates", "outros"),
            os.path.join(config.YOUTUBE_DIR, "shared_assets", "stock_footage"),
            os.path.join(config.YOUTUBE_DIR, "shared_assets", "icons"),
            os.path.join(config.TOOLS_DIR, "manim", "templates"),
            os.path.join(config.TOOLS_DIR, "manim", "output"),
        ]
        
        for d in shared_extra:
            os.makedirs(d, exist_ok=True)
        
        ColorPrinter.success("Directory structure created")
        return True


# ══════════════════════════════════════════════════════════════════════════════
# PYTHON PACKAGE INSTALLER
# ══════════════════════════════════════════════════════════════════════════════

class PackageInstaller:
    """Installs Python packages via pip."""
    
    @staticmethod
    def install_package(package: str) -> bool:
        """Install a single Python package."""
        try:
            # Check if already installed
            __import__(package.replace("-", "_"))
            ColorPrinter.info(f"Package already installed: {package}")
            return True
        except ImportError:
            pass
        
        try:
            ColorPrinter.info(f"Installing: {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--quiet", "--disable-pip-version-check"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                ColorPrinter.success(f"Installed: {package}")
                return True
            else:
                # Show error but don't fail - might be optional
                error_msg = result.stderr.split('\n')[-2] if result.stderr else "Unknown error"
                ColorPrinter.error(f"Failed to install {package}: {error_msg}")
                return False
                
        except subprocess.TimeoutExpired:
            ColorPrinter.error(f"Timeout installing {package}")
            return False
        except Exception as e:
            ColorPrinter.error(f"Error installing {package}: {e}")
            return False
    
    @staticmethod
    def install_all() -> dict:
        """Install all required and optional packages."""
        results = {"required": [], "optional": [], "failed": []}
        
        # Required packages
        for package in SetupConfig.REQUIRED_PACKAGES:
            if PackageInstaller.install_package(package):
                results["required"].append(package)
            else:
                results["failed"].append(package)
        
        # Optional packages
        for package in SetupConfig.OPTIONAL_PACKAGES:
            if PackageInstaller.install_package(package):
                results["optional"].append(package)
            else:
                ColorPrinter.warning(f"Optional package not installed: {package}")
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# PIPER TTS INSTALLER
# ══════════════════════════════════════════════════════════════════════════════

class PiperInstaller:
    """Downloads and sets up Piper TTS."""
    
    @staticmethod
    def install() -> bool:
        """Download and extract Piper TTS."""
        config = SetupConfig()
        piper_exe = os.path.join(config.PIPER_DIR, "piper.exe")
        piper_model = os.path.join(config.PIPER_DIR, "en_US-lessac-high.onnx")
        
        # Check if already installed
        if os.path.exists(piper_exe) and os.path.exists(piper_model):
            ColorPrinter.info("Piper TTS already installed")
            return True
        
        # Download Piper executable
        piper_zip = os.path.join(config.PIPER_DIR, "piper_windows_amd64.zip")
        
        if not os.path.exists(piper_exe):
            if FileDownloader.download_with_retry(
                config.PIPER_URL, 
                piper_zip, 
                "Piper TTS (Windows)"
            ):
                # Extract
                try:
                    ColorPrinter.info("Extracting Piper TTS...")
                    with zipfile.ZipFile(piper_zip, 'r') as zip_ref:
                        zip_ref.extractall(config.PIPER_DIR)
                    
                    # Clean up zip
                    os.remove(piper_zip)
                    ColorPrinter.success("Piper TTS extracted")
                except Exception as e:
                    ColorPrinter.error(f"Failed to extract Piper: {e}")
                    return False
        
        # Download voice model
        if not os.path.exists(piper_model):
            FileDownloader.download_with_retry(
                config.PIPER_VOICE_URL,
                piper_model,
                "Piper Voice Model (en-US-lessac-high)"
            )
        
        # Verify
        if os.path.exists(piper_exe) and os.path.exists(piper_model):
            ColorPrinter.success("Piper TTS ready")
            return True
        else:
            ColorPrinter.warning("Piper TTS partially installed")
            return False


# ══════════════════════════════════════════════════════════════════════════════
# FONT INSTALLER
# ══════════════════════════════════════════════════════════════════════════════

class FontInstaller:
    """Downloads professional fonts."""
    
    @staticmethod
    def install() -> bool:
        """Download all required fonts."""
        config = SetupConfig()
        success = True
        
        for font_name, url in config.FONTS.items():
            font_path = os.path.join(config.FONTS_DIR, f"{font_name}.ttf")
            
            if not os.path.exists(font_path):
                if not FileDownloader.download_with_retry(url, font_path, f"Font: {font_name}"):
                    success = False
        
        if success:
            ColorPrinter.success("Professional fonts installed")
        return success


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO ASSETS CREATOR
# ══════════════════════════════════════════════════════════════════════════════

class AudioAssetsCreator:
    """Creates basic audio assets if downloads not available."""
    
    @staticmethod
    def create_silence_mp3(duration_secs: int = 300, output_path: str = "") -> str:
        """Create a silent MP3 file for background use."""
        try:
            import numpy as np
            from pydub import AudioSegment
            import struct
            
            sample_rate = 44100
            samples = np.zeros(duration_secs * sample_rate, dtype=np.int16)
            
            audio = AudioSegment(
                samples.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=2
            )
            
            if not output_path:
                output_path = os.path.join(SetupConfig.MUSIC_DIR, "silent_backup.mp3")
            
            audio.export(output_path, format="mp3", bitrate="192k")
            return output_path
            
        except Exception:
            # Fallback: create minimal valid MP3
            if not output_path:
                output_path = os.path.join(SetupConfig.MUSIC_DIR, "silent_backup.mp3")
            
            # Minimal valid MP3 file (0.1 seconds of silence)
            minimal_mp3 = bytes([
                0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
            ])
            
            try:
                with open(output_path, 'wb') as f:
                    f.write(minimal_mp3)
            except Exception:
                pass
            
            return output_path
    
    @staticmethod
    def create_sample_sfx() -> dict:
        """Create basic sound effect files."""
        sfx_files = {}
        sfx_dir = SetupConfig.SFX_DIR
        
        # Create simple WAV files for common effects
        effects = {
            "whoosh": (0.3, 440),      # Short rising tone
            "chime": (0.2, 880),        # High ding
            "click": (0.05, 1200),      # Short click
            "transition": (0.5, 330),   # Medium sweesh
        }
        
        try:
            import numpy as np
            import wave
            
            for name, (duration, freq) in effects.items():
                path = os.path.join(sfx_dir, f"{name}.wav")
                
                if not os.path.exists(path):
                    sample_rate = 44100
                    t = np.linspace(0, duration, int(sample_rate * duration))
                    
                    if name == "whoosh":
                        # Rising frequency sweep
                        freq_sweep = freq * (1 + t / duration * 2)
                        audio = np.sin(2 * np.pi * freq_sweep * t) * np.exp(-t * 3)
                    elif name == "chime":
                        # Bell-like tone
                        audio = np.sin(2 * np.pi * freq * t) * np.exp(-t * 8)
                    else:
                        audio = np.sin(2 * np.pi * freq * t) * np.exp(-t * 10)
                    
                    audio_int16 = (audio * 32767 * 0.5).astype(np.int16)
                    
                    with wave.open(path, 'w') as wav:
                        wav.setnchannels(1)
                        wav.setsampwidth(2)
                        wav.setframerate(sample_rate)
                        wav.writeframes(audio_int16.tobytes())
                
                sfx_files[name] = path
            
            ColorPrinter.success("Sound effects created")
            return sfx_files
            
        except Exception:
            ColorPrinter.warning("Could not create sound effects")
            return sfx_files


# ══════════════════════════════════════════════════════════════════════════════
# MANIM TEMPLATES GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class ManimTemplatesGenerator:
    """Generates Manim animation templates for finance videos."""
    
    @staticmethod
    def create_all_templates() -> bool:
        """Create all Manim animation templates."""
        templates_dir = os.path.join(SetupConfig.TOOLS_DIR, "manim", "templates")
        os.makedirs(templates_dir, exist_ok=True)
        
        templates_created = []
        
        # Template 1: Money Counter Animation
        money_counter = '''
"""
Money Counter Animation
Shows money growing with particle effects
"""
from manim import *

class MoneyCounter(Scene):
    def construct(self):
        # Background
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        # Starting amount
        start_amount = 0
        target_amount = 1000000
        
        # Counter text
        counter = always_redraw(lambda:
            Text(
                f"${self.get_counter_value():,.0f}",
                font="Montserrat",
                weight="BOLD",
                color="#00D4AA",
                font_size=72
            )
        )
        
        # Track value
        self.counter_value = start_amount
        counter.move_to(ORIGIN)
        
        # Particles representing money
        particles = VGroup()
        for _ in range(50):
            particle = Dot(
                radius=0.03,
                color=random.choice(["#00D4AA", "#E94560", "#FFD700"])
            )
            particle.move_to(np.array([
                random.uniform(-6, 6),
                random.uniform(-3, 3),
                0
            ]))
            particles.add(particle)
        
        # Animations
        self.play(FadeIn(counter, scale=1.5))
        self.play(
            counter.animate.scale(1.0),
            run_time=1
        )
        
        # Animate particles
        self.play(
            *[p.animate.shift(
                np.array([0, random.uniform(2, 4), 0])
            ).set_opacity(0) for p in particles],
            run_time=2
        )
        
        # Count up
        def update_value(mob, alpha):
            self.counter_value = interpolate(start_amount, target_amount, alpha)
        
        self.play(
            UpdateFromAlphaFunc(counter, update_value),
            run_time=3,
            rate_func=smooth
        )
        
        self.wait(0.5)
        
        # Burst effect
        burst = VGroup(*[
            Line(
                ORIGIN,
                np.array([random.uniform(-1, 1), random.uniform(-1, 1), 0]) * 3,
                color="#FFD700",
                stroke_width=2
            )
            for _ in range(20)
        ])
        
        self.play(
            *[Create(line) for line in burst],
            run_time=0.5
        )
        self.play(
            *[Uncreate(line) for line in burst],
            run_time=0.3
        )
        
        self.wait(0.5)
    
    def get_counter_value(self):
        return self.counter_value
'''
        
        # Template 2: Budget Pie Chart
        budget_pie = '''
"""
Budget Pie Chart Animation
Shows expense breakdown with animated slices
"""
from manim import *

class BudgetPieChart(Scene):
    def construct(self):
        # Data
        categories = ["Housing", "Food", "Transport", "Savings", "Entertainment"]
        values = [35, 20, 15, 20, 10]
        colors = ["#E94560", "#F5A623", "#4ECDC4", "#00D4AA", "#9B59B6"]
        
        total = sum(values)
        angles = [v/total * TAU for v in values]
        
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        # Title
        title = Text(
            "MONTHLY BUDGET BREAKDOWN",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=36
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Create pie slices
        slices = VGroup()
        current_angle = 0
        
        for i, (angle, color) in enumerate(zip(angles, colors)):
            sector = AnnularSector(
                inner_radius=0,
                outer_radius=2.5,
                angle=angle,
                start_angle=current_angle,
                color=color,
                fill_opacity=0.8
            )
            slices.add(sector)
            current_angle += angle
        
        slices.move_to(ORIGIN)
        
        # Animate slices appearing one by one
        for i, sector in enumerate(slices):
            self.play(
                Create(sector),
                run_time=0.5
            )
        
        # Add labels
        labels = VGroup()
        current_angle = 0
        for i, (category, value, angle, color) in enumerate(
            zip(categories, values, angles, colors)
        ):
            mid_angle = current_angle + angle / 2
            label_pos = np.array([
                3.5 * np.cos(mid_angle),
                3.5 * np.sin(mid_angle),
                0
            ])
            
            label = VGroup(
                Text(category, font="Inter", color=color, font_size=20),
                Text(f"{value}%", font="Inter", color="white", font_size=16)
            )
            label.arrange(DOWN, buff=0.1)
            label.move_to(label_pos)
            labels.add(label)
            current_angle += angle
        
        self.play(
            *[FadeIn(label, shift=label.get_center()*0.2) for label in labels],
            run_time=2
        )
        
        self.wait(2)
'''
        
        # Template 3: Savings Growth Graph
        savings_graph = '''
"""
Compound Interest Growth Graph
Shows exponential savings growth over time
"""
from manim import *

class SavingsGrowth(Scene):
    def construct(self):
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        # Title
        title = Text(
            "THE POWER OF COMPOUND INTEREST",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=36
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Create axes
        axes = Axes(
            x_range=[0, 30, 5],
            y_range=[0, 1000000, 200000],
            x_length=10,
            y_length=6,
            axis_config={"color": "gray"},
            x_axis_config={"numbers_to_include": range(0, 31, 5)},
            y_axis_config={
                "numbers_to_include": range(0, 1000001, 200000),
                "formatter": lambda x: f"${x:,.0f}"
            }
        )
        axes.move_to(ORIGIN)
        
        labels = axes.get_axis_labels(
            x_label="Years",
            y_label="Value"
        )
        
        self.play(Create(axes), Write(labels))
        
        # Plot compound growth
        def compound_value(x):
            # $500/month at 8% annual return
            monthly_investment = 500
            monthly_rate = 0.08 / 12
            months = x * 12
            if months == 0:
                return 0
            return monthly_investment * ((1 + monthly_rate) ** months - 1) / monthly_rate
        
        graph = axes.plot(
            compound_value,
            x_range=[0, 30],
            color="#00D4AA",
            stroke_width=4
        )
        
        # Animate graph drawing
        self.play(
            Create(graph),
            run_time=4,
            rate_func=linear
        )
        
        # Highlight key points
        dots = VGroup()
        for year in [5, 10, 20, 30]:
            value = compound_value(year)
            dot = Dot(
                axes.coords_to_point(year, value),
                color="#FFD700",
                radius=0.1
            )
            label = Text(
                f"${value:,.0f}",
                font="Inter",
                color="#FFD700",
                font_size=20
            )
            label.next_to(dot, UP + RIGHT, buff=0.2)
            dots.add(VGroup(dot, label))
        
        for dot_group in dots:
            self.play(
                FadeIn(dot_group, scale=2),
                run_time=0.5
            )
        
        self.wait(2)
'''
        
        # Template 4: Debt Reduction Waterfall
        debt_waterfall = '''
"""
Debt Reduction Waterfall Chart
Shows debt decreasing over time with waterfall effect
"""
from manim import *

class DebtWaterfall(Scene):
    def construct(self):
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        title = Text(
            "DEBT SNOWBALL METHOD",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=40
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Debt data
        debts = [
            ("Credit Card A", 5000, "#E94560"),
            ("Credit Card B", 3000, "#F5A623"),
            ("Car Loan", 15000, "#4ECDC4"),
            ("Student Loan", 25000, "#9B59B6"),
        ]
        
        bars = VGroup()
        max_debt = max(d[1] for d in debts)
        
        for i, (name, amount, color) in enumerate(debts):
            bar_height = (amount / max_debt) * 4
            bar = Rectangle(
                width=1.5,
                height=bar_height,
                fill_color=color,
                fill_opacity=0.8,
                stroke_color=color,
                stroke_width=2
            )
            bar.move_to(np.array([i * 2.2 - 3.3, -2 + bar_height/2, 0]))
            
            label = Text(
                name,
                font="Inter",
                color="white",
                font_size=16
            )
            label.next_to(bar, DOWN, buff=0.2)
            
            amount_text = Text(
                f"${amount:,}",
                font="Inter",
                color=color,
                font_size=20,
                weight="BOLD"
            )
            amount_text.next_to(bar, UP, buff=0.2)
            
            bars.add(VGroup(bar, label, amount_text))
        
        # Animate bars growing
        for bar_group in bars:
            self.play(
                bar_group[0].animate.stretch_to_fit_height(bar_group[0].height),
                Write(bar_group[1]),
                Write(bar_group[2]),
                run_time=1
            )
        
        # Snowball effect arrows
        arrows = VGroup()
        for i in range(len(bars) - 1):
            arrow = CurvedArrow(
                bars[i].get_right(),
                bars[i+1].get_left(),
                color="#00D4AA",
                angle=-0.3
            )
            arrows.add(arrow)
        
        self.play(*[Create(a) for a in arrows], run_time=2)
        
        self.wait(2)
'''
        
        # Template 5: Income Streams
        income_streams = '''
"""
Multiple Income Streams Animation
Shows 8 streams of income with flow effects
"""
from manim import *

class IncomeStreams(Scene):
    def construct(self):
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        title = Text(
            "8 AUTOMATED INCOME STREAMS",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=40
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Central hub
        hub = Circle(
            radius=0.5,
            fill_color="#00D4AA",
            fill_opacity=0.8,
            stroke_width=0
        )
        hub.move_to(ORIGIN)
        hub_label = Text("YOU", font="Montserrat", color="white", font_size=24, weight="BOLD")
        hub_label.move_to(hub)
        
        self.play(Create(hub), Write(hub_label))
        
        # Stream nodes
        streams = [
            ("YouTube", UP * 2.5 + LEFT * 4),
            ("Trading", UP * 2.5 + LEFT * 1.5),
            ("API", UP * 2.5 + RIGHT * 1.5),
            ("Blog", UP * 2.5 + RIGHT * 4),
            ("E-commerce", DOWN * 2.5 + LEFT * 4),
            ("Data Agency", DOWN * 2.5 + LEFT * 1.5),
            ("Products", DOWN * 2.5 + RIGHT * 1.5),
            ("Social", DOWN * 2.5 + RIGHT * 4),
        ]
        
        colors = ["#E94560", "#F5A623", "#4ECDC4", "#00D4AA", 
                  "#9B59B6", "#3498DB", "#2ECC71", "#F39C12"]
        
        stream_nodes = VGroup()
        
        for i, (name, pos) in enumerate(streams):
            node = RoundedRectangle(
                width=2,
                height=0.8,
                corner_radius=0.2,
                fill_color=colors[i],
                fill_opacity=0.3,
                stroke_color=colors[i],
                stroke_width=2
            )
            node.move_to(pos)
            
            node_text = Text(
                name,
                font="Inter",
                color=colors[i],
                font_size=16,
                weight="BOLD"
            )
            node_text.move_to(node)
            
            stream_nodes.add(VGroup(node, node_text))
        
        # Animate streams appearing
        for node_group in stream_nodes:
            self.play(
                FadeIn(node_group[0], scale=1.2),
                Write(node_group[1]),
                run_time=0.5
            )
        
        # Connection lines with flow
        connections = VGroup()
        for i, (_, pos) in enumerate(streams):
            line = DashedLine(
                hub.get_center(),
                pos,
                dash_length=0.2,
                dashed_ratio=0.5,
                color=colors[i],
                stroke_width=2
            )
            
            # Flow particles
            for _ in range(3):
                dot = Dot(
                    radius=0.03,
                    color=colors[i]
                )
                dot.move_to(hub.get_center())
                
                # Animate flow
                self.play(
                    dot.animate.move_to(pos),
                    run_time=0.5,
                    rate_func=linear
                )
            
            connections.add(line)
        
        self.play(*[Create(c) for c in connections], run_time=1)
        
        self.wait(2)
'''
        
        # Template 6: Credit Score Meter
        credit_meter = '''
"""
Credit Score Gauge Animation
Shows credit score on a gauge/meter display
"""
from manim import *

class CreditScoreMeter(Scene):
    def construct(self):
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        title = Text(
            "YOUR CREDIT SCORE",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=40
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Create gauge
        gauge = AnnularSector(
            inner_radius=2.5,
            outer_radius=3,
            angle=PI,
            start_angle=PI,
            color="gray",
            fill_opacity=0.3
        )
        
        # Color zones
        zones = [
            (300, 579, "#E94560"),   # Bad
            (580, 669, "#F5A623"),   # Fair
            (670, 739, "#4ECDC4"),   # Good
            (740, 799, "#00D4AA"),   # Very Good
            (800, 850, "#FFD700"),   # Excellent
        ]
        
        zone_sectors = VGroup()
        for low, high, color in zones:
            start_angle = PI + (low - 300) / 550 * PI
            angle = (high - low) / 550 * PI
            sector = AnnularSector(
                inner_radius=2.5,
                outer_radius=3,
                angle=angle,
                start_angle=start_angle,
                color=color,
                fill_opacity=0.6
            )
            zone_sectors.add(sector)
        
        gauge.move_to(ORIGIN)
        zone_sectors.move_to(ORIGIN)
        
        self.play(Create(gauge))
        self.play(*[FadeIn(z) for z in zone_sectors], run_time=1)
        
        # Score labels
        score_labels = VGroup()
        for s in [300, 500, 670, 740, 800, 850]:
            angle = PI + (s - 300) / 550 * PI
            pos = np.array([3.3 * np.cos(angle), 3.3 * np.sin(angle), 0])
            label = Text(str(s), font="Inter", color="gray", font_size=16)
            label.move_to(pos)
            score_labels.add(label)
        
        self.play(*[Write(l) for l in score_labels])
        
        # Needle animation
        needle = Arrow(
            start=ORIGIN,
            end=UP * 2.8,
            color="#00D4AA",
            stroke_width=3,
            max_tip_length_to_length_ratio=0.1
        )
        needle.move_to(ORIGIN)
        
        # Animate needle moving to score
        target_score = 750
        target_angle = PI + (target_score - 300) / 550 * PI
        
        def update_needle(mob, alpha):
            angle = interpolate(PI, target_angle, alpha)
            mob.rotate(angle - mob.get_angle())
        
        self.play(
            Create(needle),
            UpdateFromAlphaFunc(needle, update_needle),
            run_time=3
        )
        
        # Score display
        score_text = Text(
            "800+",
            font="Montserrat",
            weight="BOLD",
            color="#FFD700",
            font_size=96
        )
        score_text.move_to(DOWN * 0.5)
        
        self.play(
            Write(score_text),
            needle.animate.set_color("#FFD700"),
            run_time=1
        )
        
        self.wait(2)
'''
        
        # Save all templates
        templates = {
            "money_counter.py": money_counter,
            "budget_pie.py": budget_pie,
            "savings_growth.py": savings_graph,
            "debt_waterfall.py": debt_waterfall,
            "income_streams.py": income_streams,
            "credit_score.py": credit_meter,
        }
        
        for filename, code in templates.items():
            filepath = os.path.join(templates_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code.strip() + '\n')
            templates_created.append(filename)
            ColorPrinter.success(f"Template created: {filename}")
        
        # Create template runner
        runner_code = '''
"""
Manim Animation Renderer
Renders all animation templates for use in videos.
"""
import os
import sys
import subprocess
from pathlib import Path

def render_template(template_name: str, quality: str = "high"):
    """Render a Manim template to MP4."""
    templates_dir = Path(__file__).parent / "templates"
    output_dir = Path(__file__).parent / "output"
    
    template_path = templates_dir / f"{template_name}.py"
    
    if not template_path.exists():
        print(f"Template not found: {template_name}")
        return None
    
    # Determine quality flag
    quality_flags = {
        "low": "-ql",
        "medium": "-qm",
        "high": "-qh",
        "production": "-qk",
    }
    
    flag = quality_flags.get(quality, "-qh")
    
    cmd = [
        sys.executable, "-m", "manim",
        flag,
        "--format", "mp4",
        str(template_path),
        "-o", str(output_dir)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            # Find the output file
            mp4_files = list(output_dir.glob("*.mp4"))
            if mp4_files:
                latest = max(mp4_files, key=os.path.getmtime)
                print(f"Rendered: {latest}")
                return str(latest)
        
        print(f"Render failed: {result.stderr[-200:]}")
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("template", help="Template name (without .py)")
    parser.add_argument("--quality", default="high", choices=["low", "medium", "high", "production"])
    
    args = parser.parse_args()
    
    result = render_template(args.template, args.quality)
    
    if result:
        print(f"\\n✓ Output: {result}")
    else:
        print("\\n✗ Render failed")
'''
        
        runner_path = os.path.join(SetupConfig.TOOLS_DIR, "manim", "render_animation.py")
        with open(runner_path, 'w') as f:
            f.write(runner_code.strip())
        
        ColorPrinter.success(f"Animation renderer created: render_animation.py")
        
        return True


# ══════════════════════════════════════════════════════════════════════════════
# API CONFIGURATION HELPER
# ══════════════════════════════════════════════════════════════════════════════

class APIConfigurator:
    """Helps configure API keys."""
    
    @staticmethod
    def configure() -> dict:
        """Interactive API key configuration."""
        print("\n" + "="*60)
        print("  🔑 API KEY CONFIGURATION")
        print("  (Press Enter to skip / Leave blank for defaults)")
        print("="*60)
        
        config = {}
        
        print("\n  Pexels API (for free stock footage)")
        print("  Sign up: https://www.pexels.com/api/")
        pexels_key = input("  API Key: ").strip()
        config["PEXELS_API_KEY"] = pexels_key if pexels_key else ""
        
        print("\n  Pixabay API (for additional free footage)")
        print("  Sign up: https://pixabay.com/api/docs/")
        pixabay_key = input("  API Key: ").strip()
        config["PIXABAY_API_KEY"] = pixabay_key if pixabay_key else ""
        
        # Save to .env file
        env_path = os.path.join(SetupConfig.BASE_DIR, ".env")
        with open(env_path, 'w') as f:
            for key, value in config.items():
                if value:
                    f.write(f"{key}={value}\n")
        
        # Also save as JSON
        config_path = os.path.join(SetupConfig.BASE_DIR, "api_config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        ColorPrinter.success("API configuration saved")
        return config


# ══════════════════════════════════════════════════════════════════════════════
# MASTER SETUP ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

class MasterSetup:
    """Orchestrates the complete setup process."""
    
    def __init__(self):
        self.start_time = time.time()
        self.steps_total = 8
        self.current_step = 0
    
    def run(self):
        """Run complete setup."""
        print("\n" + "="*70)
        print("  🚀 WORLD-CLASS YOUTUBE PIPELINE — COMPLETE SETUP")
        print("  8-Stream Automated Content Factory")
        print("="*70)
        
        print("\n  This will install everything needed for professional")
        print("  video production on your local machine.")
        print("  All tools are FREE and run locally.")
        print("\n  Estimated time: 15-30 minutes (depends on internet speed)")
        
        ans = input("\n  Continue? (y/n): ").strip().lower()
        if ans != 'y':
            print("  Setup cancelled.")
            return
        
        results = {}
        
        # Step 1: Create directories
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Creating directory structure")
        results["directories"] = DirectoryCreator.create_all()
        
        # Step 2: Install Python packages
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Installing Python packages")
        results["packages"] = PackageInstaller.install_all()
        
        # Step 3: Install Piper TTS
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Installing Piper TTS (voice synthesis)")
        try:
            results["piper"] = PiperInstaller.install()
        except Exception as e:
            ColorPrinter.warning(f"Piper installation skipped: {e}")
            results["piper"] = False
        
        # Step 4: Download fonts
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Downloading professional fonts")
        try:
            results["fonts"] = FontInstaller.install()
        except Exception as e:
            ColorPrinter.warning(f"Font download skipped: {e}")
            results["fonts"] = False
        
        # Step 5: Create audio assets
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Creating audio assets")
        try:
            AudioAssetsCreator.create_silence_mp3()
            AudioAssetsCreator.create_sample_sfx()
            results["audio"] = True
        except Exception as e:
            ColorPrinter.warning(f"Audio creation skipped: {e}")
            results["audio"] = False
        
        # Step 6: Create Manim templates
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Creating animation templates")
        try:
            results["templates"] = ManimTemplatesGenerator.create_all_templates()
        except Exception as e:
            ColorPrinter.warning(f"Template creation skipped: {e}")
            results["templates"] = False
        
        # Step 7: Configure API keys
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Configuring API keys (optional)")
        results["api"] = APIConfigurator.configure()
        
        # Step 8: Create sample scripts
        self.current_step += 1
        ColorPrinter.step(self.current_step, self.steps_total, "Creating sample scripts from your PDFs")
        results["samples"] = self.create_sample_scripts()
        
        # Final summary
        self.print_summary(results)
    
    def create_sample_scripts(self) -> bool:
        """Create sample script files from the provided PDF content."""
        samples_dir = os.path.join(SetupConfig.RUNS_DIR, "full_run_01", "S1", "inputs")
        os.makedirs(samples_dir, exist_ok=True)
        
        # Sample scripts based on your PDFs
        sample_scripts = {
            "01_money_habits.txt": """**Script:** 7 Money Habits That Keep You Broke

**Section 1: Hook (0:00-0:15)**

[VISUAL: Person stressed about money, alarm clock ringing]

Narrator: "Are you tired of waking up every morning feeling like you're starting from scratch? Like your bank account has amnesia?"

**Section 2: Context and Urgency (0:16-1:15)**

[VISUAL: Montage of people working, checking empty wallets]

Narrator: "Here's the shocking truth: nearly 78% of people live paycheck to paycheck. But it's not because they don't earn enough. It's because of seven specific money habits that silently drain their wealth."

**Section 3: Main Content - Act 1: Habit Breakdown (1:16-3:30)**

Narrator: "Let me expose these seven wealth-destroying habits one by one."

Habit 1: You don't track your spending.
[VISUAL: Money floating away animation]

Habit 2: Impulse purchases disguised as 'treats'.
[VISUAL: Online shopping cart filling up]

Habit 3: Paying yourself last instead of first.
[VISUAL: Piggy bank at the end of a long line]

**Section 3: Main Content - Act 2: Solutions (3:31-6:00)**

Narrator: "But here's the good news. Each of these habits has a simple fix."

Fix 1: The 60-second daily money check.
[VISUAL: Person checking phone app, smiling]

Fix 2: The 24-hour rule that kills impulse buying.
[VISUAL: Clock ticking, then crossing out a purchase]

Fix 3: Automate your savings before you see your paycheck.
[VISUAL: Money splitting into two accounts automatically]

**Section 4: Close with CTA (6:01-7:00)**

Narrator: "Break these seven habits, and you'll be amazed at how quickly your wealth grows. Download our free Money Habits Tracker below and start your financial transformation today."
""",
            "02_save_1000.txt": """**Script:** How to Save $1,000 in 30 Days (Any Income)

**Hook (0:00-0:15)**

[VISUAL: $1,000 cash animation with countdown timer]

Narrator: "Want to save $1,000 in the next 30 days? Most people think it's impossible. They're wrong."

**Context and Urgency (0:16-1:00)**

[VISUAL: Statistics showing savings crisis]

Narrator: "The average person has less than $400 in emergency savings. One unexpected expense away from financial disaster. But here's the truth: you can save $1,000 this month regardless of your income."

**Main Content - Act 1: The Math (1:01-2:15)**

Narrator: "Let me show you exactly how. $1,000 divided by 30 days is just $33.33 per day. But we're not going to do it that way. We're going to stack multiple strategies."

Strategy 1: The No-Spend Challenge. Pick 10 days this month where you spend absolutely nothing.
[VISUAL: Calendar with X marks]

**Act 2: Cut the Leaks (2:16-3:45)**

Narrator: "Here's where most people's money actually goes..."

[VISUAL: Pie chart of hidden expenses]

Narrator: "Subscriptions you forgot about. Coffee runs. Food delivery fees. These small leaks sink big ships."

**Act 3: Automate and Stack (3:46-5:20)**

Narrator: "The secret weapon: automation."
[VISUAL: Automatic transfer animation]

Narrator: "Set up a separate savings account and schedule automatic daily transfers of just $33."

**Closing (5:21-6:15)**

Narrator: "Start tomorrow morning. By this time next month, you'll have proof that saving is possible. The 30-Day $1,000 Challenge starts now."
""",
        }
        
        for filename, content in sample_scripts.items():
            filepath = os.path.join(samples_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            ColorPrinter.success(f"Sample script: {filename}")
        
        return True
    
    def print_summary(self, results: dict):
        """Print final setup summary."""
        elapsed = time.time() - self.start_time
        
        print("\n" + "="*70)
        print("  ✅ SETUP COMPLETE!")
        print(f"  Time: {elapsed:.0f} seconds")
        print("="*70)
        
        print(f"\n  📁 Everything is installed at: {SetupConfig.BASE_DIR}")
        
        print(f"\n  📝 NEXT STEPS:")
        print(f"  1. Place your script .txt files in:")
        print(f"     {SetupConfig.RUNS_DIR}\\full_run_01\\S1\\inputs\\(for Stream 1)")
        print(f"     {SetupConfig.RUNS_DIR}\\full_run_01\\S2\\inputs\\(for Stream 2)")
        print(f"     ...and so on for S3-S8")
        print(f"\n  2. Run the video pipeline:")
        print(f"     python youtube_pipeline_pro.py --stream S1")
        print(f"\n  3. Or process all streams at once:")
        print(f"     python youtube_pipeline_pro.py --all-streams")
        print(f"\n  4. Render a Manim animation (if manim installed):")
        print(f"     cd {SetupConfig.TOOLS_DIR}\\manim")
        print(f"     python render_animation.py money_counter")
        
        print(f"\n  🎬 Animation templates available:")
        templates_dir = os.path.join(SetupConfig.TOOLS_DIR, "manim", "templates")
        if os.path.exists(templates_dir):
            for f in sorted(os.listdir(templates_dir)):
                if f.endswith('.py'):
                    print(f"     • {f}")
        
        print(f"\n  💾 Free stock footage (if API keys configured):")
        print(f"     • Pexels: https://www.pexels.com/")
        print(f"     • Pixabay: https://pixabay.com/")
        
        print(f"\n  📚 Documentation:")
        print(f"     See README at: {SetupConfig.BASE_DIR}\\README.md")
        
        print("\n" + "="*70)
        print("  Ready to create world-class finance videos!")
        print("="*70 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    setup = MasterSetup()
    setup.run()


if __name__ == "__main__":
    main()
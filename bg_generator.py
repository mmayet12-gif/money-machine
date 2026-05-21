#!/usr/bin/env python3
"""
Cinematic Background Generator — 48+ premium backgrounds across 9 categories.

Categories:
  1. Luxury multi-stop gradients (8)
  2. Abstract geometric patterns (6)
  3. Cityscape silhouettes (4)
  4. Wealth symbol compositions (4)
  5. Particle fields / constellations (5)
  6. Radial burst / spotlight (4)
  7. Procedural marble textures (4)
  8. Data visualization aesthetics (5)
  9. Cinematic light leaks (4)

All backgrounds are 1920x1080 JPG, generated once during --setup.
Each gets mood tags for intelligent scene matching.

Usage:
    from bg_generator import generate_all_backgrounds
    paths = generate_all_backgrounds(Path("assets/backgrounds"))
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080


# ===========================================================================
# UTILITY FUNCTIONS
# ===========================================================================

def _noise_layer(w: int, h: int, scale: int = 32, seed: int = 0) -> np.ndarray:
    """Generate smooth noise via upscaled random grid. Returns 0-1 float array."""
    rng = np.random.RandomState(seed)
    small_w = max(2, w // scale)
    small_h = max(2, h // scale)
    small = rng.random((small_h, small_w)).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8), "L")
    img = img.resize((w, h), Image.BILINEAR)
    return np.array(img).astype(np.float64) / 255.0


def _multi_stop_gradient(h: int, w: int, stops: list[tuple[float, tuple]]) -> np.ndarray:
    """Create vertical gradient with multiple color stops. Returns HxWx3 float64."""
    positions = [s[0] for s in stops]
    colors = [s[1] for s in stops]
    arr = np.zeros((h, w, 3), dtype=np.float64)
    for ch in range(3):
        ch_vals = [c[ch] for c in colors]
        col = np.interp(np.linspace(0, 1, h), positions, ch_vals)
        arr[:, :, ch] = col[:, np.newaxis]
    return arr


def _radial_falloff(h: int, w: int, cx: float, cy: float,
                    radius: float = 500.0) -> np.ndarray:
    """Radial distance-based falloff. Returns 0-1 array, 1 at center."""
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    return np.clip(1.0 - dist / radius, 0, 1)


def _add_dither(arr: np.ndarray, intensity: float = 3.0, seed: int = 42) -> np.ndarray:
    """Add subtle noise to prevent color banding."""
    rng = np.random.RandomState(seed)
    noise = rng.normal(0, intensity, arr.shape)
    return np.clip(arr + noise, 0, 255)


def _elliptical_blob(h: int, w: int, cx: float, cy: float,
                     sx: float, sy: float, intensity: float = 1.0) -> np.ndarray:
    """Gaussian elliptical blob. Returns 0-intensity array."""
    Y, X = np.ogrid[:h, :w]
    dist = (X - cx) ** 2 / (sx ** 2 + 1e-6) + (Y - cy) ** 2 / (sy ** 2 + 1e-6)
    return intensity * np.exp(-dist * 0.5)


def _to_image(arr: np.ndarray, seed: int = 0) -> Image.Image:
    """Convert float64 array to PIL Image with dithering."""
    arr = _add_dither(arr, intensity=2.5, seed=seed)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# ===========================================================================
# CATEGORY 1: LUXURY MULTI-STOP GRADIENTS (8 variants)
# ===========================================================================

GRADIENT_THEMES = [
    {
        "name": "deep_abyss",
        "stops": [(0.0, (5, 5, 18)), (0.3, (15, 10, 45)), (0.65, (8, 22, 38)), (1.0, (2, 2, 8))],
        "accent": (218, 175, 65), "glow_pos": (0.7, 0.3), "mood": "dramatic",
    },
    {
        "name": "gold_vault",
        "stops": [(0.0, (25, 18, 5)), (0.35, (40, 30, 8)), (0.7, (20, 14, 5)), (1.0, (5, 3, 0))],
        "accent": (255, 215, 80), "glow_pos": (0.3, 0.4), "mood": "luxury",
    },
    {
        "name": "emerald_night",
        "stops": [(0.0, (3, 18, 12)), (0.4, (5, 35, 22)), (0.75, (8, 22, 16)), (1.0, (2, 8, 5))],
        "accent": (50, 255, 150), "glow_pos": (0.6, 0.5), "mood": "wealth",
    },
    {
        "name": "royal_purple",
        "stops": [(0.0, (18, 5, 30)), (0.3, (30, 8, 55)), (0.6, (20, 12, 40)), (1.0, (5, 2, 12))],
        "accent": (200, 160, 255), "glow_pos": (0.4, 0.3), "mood": "luxury",
    },
    {
        "name": "crimson_noir",
        "stops": [(0.0, (25, 5, 5)), (0.35, (45, 10, 12)), (0.7, (20, 5, 8)), (1.0, (5, 0, 2))],
        "accent": (255, 80, 80), "glow_pos": (0.5, 0.4), "mood": "dramatic",
    },
    {
        "name": "midnight_steel",
        "stops": [(0.0, (12, 14, 20)), (0.4, (22, 26, 38)), (0.7, (15, 18, 28)), (1.0, (4, 5, 10))],
        "accent": (180, 200, 240), "glow_pos": (0.5, 0.5), "mood": "professional",
    },
    {
        "name": "bronze_horizon",
        "stops": [(0.0, (8, 5, 2)), (0.3, (45, 30, 10)), (0.6, (30, 18, 5)), (1.0, (5, 3, 1))],
        "accent": (255, 200, 100), "glow_pos": (0.5, 0.6), "mood": "warm",
    },
    {
        "name": "arctic_blue",
        "stops": [(0.0, (5, 12, 25)), (0.35, (10, 25, 55)), (0.7, (5, 18, 40)), (1.0, (2, 5, 12))],
        "accent": (100, 200, 255), "glow_pos": (0.4, 0.3), "mood": "tech",
    },
]


def generate_luxury_gradient(theme: dict, seed: int, dest: Path) -> dict:
    arr = _multi_stop_gradient(H, W, theme["stops"])

    # Add radial glow from accent
    gx, gy = theme["glow_pos"]
    glow = _radial_falloff(H, W, gx * W, gy * H, radius=800)
    accent = np.array(theme["accent"], dtype=np.float64)
    for ch in range(3):
        arr[:, :, ch] += glow * accent[ch] * 0.08

    # Add diagonal sweep gradient (rotated 30 degrees)
    rng = np.random.RandomState(seed)
    angle = rng.uniform(20, 40)
    rad = math.radians(angle)
    Y, X = np.mgrid[:H, :W]
    rotated = X * math.cos(rad) + Y * math.sin(rad)
    rotated = (rotated - rotated.min()) / (rotated.max() - rotated.min() + 1e-8)
    for ch in range(3):
        arr[:, :, ch] += rotated * accent[ch] * 0.03

    # Bokeh orbs
    img = _to_image(arr, seed)
    img = img.convert("RGBA")
    for _ in range(rng.randint(10, 22)):
        cx = rng.randint(0, W)
        cy = rng.randint(0, H)
        r = rng.randint(40, 250)
        alpha = rng.randint(6, 28)
        orb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(orb)
        color = (*theme["accent"], alpha)
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)
        blur_r = max(1, r // 3)
        orb = orb.filter(ImageFilter.GaussianBlur(radius=blur_r))
        img = Image.alpha_composite(img, orb)

    img.convert("RGB").save(dest, "JPEG", quality=93)
    return {"category": "gradient", "mood": theme["mood"], "accent": list(theme["accent"]),
            "name": theme["name"]}


# ===========================================================================
# CATEGORY 2: ABSTRACT GEOMETRIC PATTERNS (6 variants)
# ===========================================================================

GEOMETRIC_VARIANTS = [
    {"name": "hex_grid", "type": "hexagon", "mood": "tech",
     "base": [(0.0, (5, 8, 18)), (1.0, (2, 3, 10))], "accent": (0, 200, 255)},
    {"name": "golden_spiral", "type": "spiral", "mood": "luxury",
     "base": [(0.0, (12, 10, 5)), (1.0, (3, 2, 0))], "accent": (218, 175, 65)},
    {"name": "circuit_board", "type": "circuit", "mood": "tech",
     "base": [(0.0, (8, 12, 20)), (1.0, (2, 4, 10))], "accent": (50, 255, 150)},
    {"name": "concentric_rings", "type": "concentric", "mood": "dramatic",
     "base": [(0.0, (10, 5, 18)), (1.0, (3, 1, 8))], "accent": (200, 160, 255)},
    {"name": "triangle_mesh", "type": "triangles", "mood": "professional",
     "base": [(0.0, (10, 12, 15)), (1.0, (3, 4, 6))], "accent": (180, 200, 240)},
    {"name": "dot_matrix", "type": "dots", "mood": "professional",
     "base": [(0.0, (8, 8, 12)), (1.0, (2, 2, 4))], "accent": (255, 215, 80)},
]


def generate_geometric(variant: dict, seed: int, dest: Path) -> dict:
    rng = random.Random(seed)
    arr = _multi_stop_gradient(H, W, variant["base"])
    img = _to_image(arr, seed).convert("RGBA")
    draw = ImageDraw.Draw(img)
    accent = variant["accent"]
    vtype = variant["type"]

    if vtype == "hexagon":
        hex_r = 60
        hex_w = hex_r * 2
        hex_h = int(hex_r * math.sqrt(3))
        for row in range(H // hex_h + 2):
            for col in range(W // hex_w + 2):
                cx = col * int(hex_w * 0.75) + (hex_r if row % 2 else 0)
                cy = row * hex_h
                pts = [(cx + int(hex_r * math.cos(math.radians(60 * i + 30))),
                        cy + int(hex_r * math.sin(math.radians(60 * i + 30))))
                       for i in range(6)]
                alpha = rng.randint(8, 22)
                draw.polygon(pts, outline=(*accent, alpha))
                if rng.random() < 0.18:
                    draw.polygon(pts, fill=(*accent, rng.randint(6, 18)))

    elif vtype == "spiral":
        cx, cy = W * 0.45, H * 0.55
        golden = (1 + math.sqrt(5)) / 2
        points = []
        for i in range(600):
            angle = i * 2.4
            r = math.sqrt(i) * 12
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if 0 <= x < W and 0 <= y < H:
                points.append((int(x), int(y)))
                sz = max(1, int(3 - i / 250))
                alpha = max(5, 35 - i // 20)
                draw.ellipse([(int(x) - sz, int(y) - sz), (int(x) + sz, int(y) + sz)],
                             fill=(*accent, alpha))
        for i in range(1, len(points)):
            if rng.random() < 0.3:
                draw.line([points[i - 1], points[i]], fill=(*accent, 12), width=1)

    elif vtype == "circuit":
        grid = 80
        for _ in range(120):
            x = rng.randint(0, W // grid) * grid
            y = rng.randint(0, H // grid) * grid
            direction = rng.choice(["h", "v"])
            length = rng.randint(1, 5) * grid
            alpha = rng.randint(15, 40)
            if direction == "h":
                draw.line([(x, y), (x + length, y)], fill=(*accent, alpha), width=1)
                # corner
                if rng.random() < 0.5:
                    vy = rng.choice([-1, 1]) * rng.randint(1, 3) * grid
                    draw.line([(x + length, y), (x + length, y + vy)],
                              fill=(*accent, alpha), width=1)
            else:
                draw.line([(x, y), (x, y + length)], fill=(*accent, alpha), width=1)
            # junction dot
            draw.ellipse([(x - 3, y - 3), (x + 3, y + 3)], fill=(*accent, alpha + 10))

    elif vtype == "concentric":
        cx, cy = W * 0.55, H * 0.48
        for i in range(30):
            r = 30 + i * 35
            alpha = max(5, 30 - i)
            draw.ellipse([(int(cx - r), int(cy - r)), (int(cx + r), int(cy + r))],
                         outline=(*accent, alpha), width=1)

    elif vtype == "triangles":
        points = [(rng.randint(0, W), rng.randint(0, H)) for _ in range(60)]
        for i in range(len(points)):
            closest = sorted(range(len(points)),
                             key=lambda j: math.hypot(points[j][0] - points[i][0],
                                                      points[j][1] - points[i][1]))[:4]
            for j in closest[1:]:
                alpha = rng.randint(8, 25)
                draw.line([points[i], points[j]], fill=(*accent, alpha), width=1)
        for p in points:
            sz = rng.randint(2, 5)
            draw.ellipse([(p[0] - sz, p[1] - sz), (p[0] + sz, p[1] + sz)],
                         fill=(*accent, rng.randint(20, 50)))

    elif vtype == "dots":
        spacing = 40
        cx_center, cy_center = W // 2, H // 2
        max_dist = math.hypot(cx_center, cy_center)
        for x in range(0, W, spacing):
            for y in range(0, H, spacing):
                dist = math.hypot(x - cx_center, y - cy_center)
                brightness = 1.0 - (dist / max_dist) * 0.7
                r = int(2 + brightness * 3)
                alpha = int(10 + brightness * 30)
                draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(*accent, alpha))

    img.convert("RGB").save(dest, "JPEG", quality=93)
    return {"category": "geometric", "mood": variant["mood"], "accent": list(accent),
            "name": variant["name"]}


# ===========================================================================
# CATEGORY 3: CITYSCAPE SILHOUETTES (4 variants)
# ===========================================================================

CITYSCAPE_THEMES = [
    {"name": "manhattan_night", "sky": [(0.0, (5, 10, 30)), (0.6, (8, 15, 35)), (1.0, (2, 3, 8))],
     "accent": (255, 200, 80), "glow_color": (20, 30, 60), "mood": "aspirational"},
    {"name": "dubai_gold", "sky": [(0.0, (20, 15, 5)), (0.5, (30, 20, 8)), (1.0, (5, 3, 1))],
     "accent": (255, 215, 100), "glow_color": (40, 30, 10), "mood": "luxury"},
    {"name": "tokyo_neon", "sky": [(0.0, (10, 5, 25)), (0.5, (15, 8, 35)), (1.0, (3, 1, 10))],
     "accent": (255, 50, 180), "glow_color": (25, 10, 40), "mood": "tech"},
    {"name": "london_fog", "sky": [(0.0, (15, 18, 22)), (0.5, (20, 22, 28)), (1.0, (5, 6, 8))],
     "accent": (180, 200, 230), "glow_color": (18, 20, 25), "mood": "professional"},
]


def generate_cityscape(theme: dict, seed: int, dest: Path) -> dict:
    rng = random.Random(seed)
    arr = _multi_stop_gradient(H, W, theme["sky"])
    img = _to_image(arr, seed).convert("RGBA")
    accent = theme["accent"]

    # Horizon glow
    glow_strip = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_strip)
    horizon_y = int(H * 0.65)
    gc = theme["glow_color"]
    for i in range(80):
        alpha = max(1, 40 - i)
        gd.line([(0, horizon_y - i), (W, horizon_y - i)], fill=(*gc, alpha))
        gd.line([(0, horizon_y + i), (W, horizon_y + i)], fill=(*gc, alpha))
    glow_strip = glow_strip.filter(ImageFilter.GaussianBlur(radius=15))
    img = Image.alpha_composite(img, glow_strip)

    # Buildings — 3 depth layers
    draw = ImageDraw.Draw(img)
    for layer in range(3):
        darkness = [18, 12, 6][layer]
        n_buildings = [15, 20, 25][layer]
        base_y = horizon_y + layer * 5

        for _ in range(n_buildings):
            bw = rng.randint(25, 80)
            bh = rng.randint(100, 500 - layer * 100)
            bx = rng.randint(-20, W)
            by = base_y - bh

            # Building body
            color = (darkness, darkness, darkness + 3, 220)
            draw.rectangle([(bx, by), (bx + bw, base_y + 50)], fill=color)

            # Antenna on tall buildings
            if bh > 350 and rng.random() < 0.4:
                ax = bx + bw // 2
                draw.line([(ax, by - 30), (ax, by)], fill=(darkness + 5, darkness + 5, darkness + 8, 200), width=2)

            # Window lights
            if layer >= 1:
                for wx in range(bx + 5, bx + bw - 5, 12):
                    for wy in range(by + 8, base_y - 5, 16):
                        if rng.random() < 0.35:
                            alpha = rng.randint(30, 90)
                            warm = (rng.randint(200, 255), rng.randint(180, 230),
                                    rng.randint(100, 170), alpha)
                            draw.rectangle([(wx, wy), (wx + 4, wy + 6)], fill=warm)

    # City accent glow at base
    for _ in range(rng.randint(3, 6)):
        cx = rng.randint(100, W - 100)
        blob = _elliptical_blob(H, W, cx, horizon_y, 200, 80, 0.15)
        blob_rgb = np.zeros((H, W, 4), dtype=np.float64)
        for ch in range(3):
            blob_rgb[:, :, ch] = blob * accent[ch]
        blob_rgb[:, :, 3] = blob * 60
        blob_img = Image.fromarray(np.clip(blob_rgb, 0, 255).astype(np.uint8), "RGBA")
        blob_img = blob_img.filter(ImageFilter.GaussianBlur(radius=30))
        img = Image.alpha_composite(img, blob_img)

    img.convert("RGB").save(dest, "JPEG", quality=93)
    return {"category": "cityscape", "mood": theme["mood"], "accent": list(accent),
            "name": theme["name"]}


# ===========================================================================
# CATEGORY 4: WEALTH SYMBOL COMPOSITIONS (4 variants)
# ===========================================================================

WEALTH_THEMES = [
    {"name": "diamond_facets", "type": "diamond", "mood": "luxury",
     "base": [(0.0, (8, 5, 18)), (1.0, (2, 1, 5))], "accent": (180, 220, 255)},
    {"name": "growth_bars", "type": "bars", "mood": "wealth",
     "base": [(0.0, (5, 12, 8)), (1.0, (1, 4, 2))], "accent": (50, 255, 120)},
    {"name": "crown_motif", "type": "crown", "mood": "luxury",
     "base": [(0.0, (18, 14, 5)), (1.0, (5, 3, 0))], "accent": (255, 215, 0)},
    {"name": "coin_abstract", "type": "coins", "mood": "wealth",
     "base": [(0.0, (15, 12, 5)), (1.0, (4, 3, 1))], "accent": (255, 200, 80)},
]


def generate_wealth_symbols(theme: dict, seed: int, dest: Path) -> dict:
    rng = random.Random(seed)
    arr = _multi_stop_gradient(H, W, theme["base"])
    img = _to_image(arr, seed).convert("RGBA")
    draw = ImageDraw.Draw(img)
    accent = theme["accent"]
    vtype = theme["type"]

    if vtype == "diamond":
        for _ in range(rng.randint(5, 10)):
            cx = rng.randint(100, W - 100)
            cy = rng.randint(100, H - 100)
            size = rng.randint(60, 200)
            alpha = rng.randint(10, 30)
            pts = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
            draw.polygon(pts, outline=(*accent, alpha + 15))
            # Inner facet lines
            draw.line([(cx, cy - size), (cx + size // 2, cy)], fill=(*accent, alpha), width=1)
            draw.line([(cx, cy - size), (cx - size // 2, cy)], fill=(*accent, alpha), width=1)
            draw.line([(cx, cy + size), (cx + size // 2, cy)], fill=(*accent, alpha), width=1)
            draw.line([(cx, cy + size), (cx - size // 2, cy)], fill=(*accent, alpha), width=1)

    elif vtype == "bars":
        n_bars = rng.randint(8, 15)
        bar_w = int(W * 0.6 / n_bars)
        start_x = int(W * 0.2)
        base_y = int(H * 0.75)
        for i in range(n_bars):
            h_pct = 0.15 + (i / n_bars) * 0.5 + rng.uniform(-0.05, 0.05)
            bar_h = int(H * h_pct)
            bx = start_x + i * (bar_w + 8)
            by = base_y - bar_h
            # Gradient fill per bar
            for row in range(bar_h):
                t = row / max(1, bar_h)
                alpha = int(15 + t * 40)
                r = int(accent[0] * t)
                g = int(accent[1] * t)
                b = int(accent[2] * t)
                draw.line([(bx, by + row), (bx + bar_w, by + row)], fill=(r, g, b, alpha))
            draw.rectangle([(bx, by), (bx + bar_w, base_y)], outline=(*accent, 25))

        # Trend line
        points = []
        for i in range(n_bars):
            h_pct = 0.15 + (i / n_bars) * 0.5
            bx = start_x + i * (bar_w + 8) + bar_w // 2
            by = base_y - int(H * h_pct)
            points.append((bx, by))
        if len(points) > 1:
            draw.line(points, fill=(*accent, 50), width=2)

    elif vtype == "crown":
        # Large stylized crown
        cx, cy = W // 2, H // 3
        cw, ch = 350, 200
        crown_pts = [
            (cx - cw, cy + ch), (cx - cw, cy),
            (cx - cw * 2 // 3, cy - ch // 2),
            (cx - cw // 3, cy), (cx, cy - ch),
            (cx + cw // 3, cy), (cx + cw * 2 // 3, cy - ch // 2),
            (cx + cw, cy), (cx + cw, cy + ch),
        ]
        draw.polygon(crown_pts, outline=(*accent, 35), fill=(*accent, 8))
        # Jewel dots on peaks
        for pt in [crown_pts[2], crown_pts[4], crown_pts[6]]:
            draw.ellipse([(pt[0] - 8, pt[1] - 8), (pt[0] + 8, pt[1] + 8)],
                         fill=(*accent, 50))
        # Smaller scattered crowns
        for _ in range(rng.randint(4, 8)):
            sx = rng.randint(50, W - 50)
            sy = rng.randint(50, H - 50)
            scale = rng.uniform(0.1, 0.25)
            alpha = rng.randint(6, 18)
            small_pts = [(int(sx + (px - cx) * scale), int(sy + (py - cy) * scale))
                         for px, py in crown_pts]
            draw.polygon(small_pts, outline=(*accent, alpha))

    elif vtype == "coins":
        for _ in range(rng.randint(8, 15)):
            cx = rng.randint(100, W - 100)
            cy = rng.randint(80, H - 80)
            r = rng.randint(40, 120)
            alpha = rng.randint(10, 28)
            draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(*accent, alpha + 10))
            # Inner ring
            draw.ellipse([(cx - r + 10, cy - r + 10), (cx + r - 10, cy + r - 10)],
                         outline=(*accent, alpha))
            # Dollar/currency mark (simple cross)
            draw.line([(cx, cy - r // 3), (cx, cy + r // 3)], fill=(*accent, alpha), width=2)
            draw.line([(cx - r // 4, cy), (cx + r // 4, cy)], fill=(*accent, alpha), width=1)

    img.convert("RGB").save(dest, "JPEG", quality=93)
    return {"category": "wealth_symbol", "mood": theme["mood"], "accent": list(accent),
            "name": theme["name"]}


# ===========================================================================
# CATEGORY 5: PARTICLE FIELDS / CONSTELLATIONS (5 variants)
# ===========================================================================

PARTICLE_THEMES = [
    {"name": "star_field", "density": 200, "connect_dist": 120, "mood": "dramatic",
     "base": [(0.0, (3, 3, 10)), (1.0, (0, 0, 3))], "accent": (220, 230, 255)},
    {"name": "neural_net", "density": 100, "connect_dist": 180, "mood": "tech",
     "base": [(0.0, (5, 10, 18)), (1.0, (1, 3, 8))], "accent": (0, 200, 255)},
    {"name": "gold_dust", "density": 300, "connect_dist": 80, "mood": "luxury",
     "base": [(0.0, (10, 8, 3)), (1.0, (3, 2, 0))], "accent": (255, 215, 80)},
    {"name": "constellation_map", "density": 60, "connect_dist": 250, "mood": "professional",
     "base": [(0.0, (5, 5, 15)), (1.0, (1, 1, 5))], "accent": (180, 200, 240)},
    {"name": "emerald_particles", "density": 150, "connect_dist": 130, "mood": "wealth",
     "base": [(0.0, (3, 12, 8)), (1.0, (0, 4, 2))], "accent": (50, 255, 150)},
]


def generate_particle_field(theme: dict, seed: int, dest: Path) -> dict:
    rng = random.Random(seed)
    arr = _multi_stop_gradient(H, W, theme["base"])
    img = _to_image(arr, seed).convert("RGBA")
    draw = ImageDraw.Draw(img)
    accent = theme["accent"]

    # Generate points with importance weighting
    points = []
    for _ in range(theme["density"]):
        x = rng.randint(20, W - 20)
        y = rng.randint(20, H - 20)
        importance = rng.random()
        points.append((x, y, importance))

    # Draw connections
    conn_dist = theme["connect_dist"]
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < conn_dist:
                alpha = int(max(3, 18 * (1 - dist / conn_dist)))
                draw.line([(points[i][0], points[i][1]), (points[j][0], points[j][1])],
                          fill=(*accent, alpha), width=1)

    # Draw points
    for x, y, imp in points:
        r = int(1 + imp * 4)
        alpha = int(15 + imp * 55)
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(*accent, alpha))

    # Bright stars with glow
    bright = sorted(points, key=lambda p: p[2], reverse=True)[:8]
    for x, y, imp in bright:
        glow_r = int(15 + imp * 25)
        orb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(orb)
        od.ellipse([(x - glow_r, y - glow_r), (x + glow_r, y + glow_r)],
                   fill=(*accent, int(20 + imp * 30)))
        orb = orb.filter(ImageFilter.GaussianBlur(radius=glow_r // 2))
        img = Image.alpha_composite(img, orb)

    img.convert("RGB").save(dest, "JPEG", quality=93)
    return {"category": "particle_field", "mood": theme["mood"], "accent": list(accent),
            "name": theme["name"]}


# ===========================================================================
# CATEGORY 6: RADIAL BURST / SPOTLIGHT (4 variants)
# ===========================================================================

RADIAL_THEMES = [
    {"name": "golden_spotlight", "mood": "luxury",
     "base": [(0.0, (5, 4, 2)), (1.0, (1, 1, 0))],
     "lights": [(0.35, 0.45, 500, (255, 200, 80), 0.2), (0.7, 0.6, 350, (255, 180, 50), 0.12)]},
    {"name": "dual_beam", "mood": "dramatic",
     "base": [(0.0, (5, 3, 12)), (1.0, (1, 0, 4))],
     "lights": [(0.2, 0.3, 550, (100, 180, 255), 0.18), (0.8, 0.7, 450, (255, 80, 150), 0.15)]},
    {"name": "center_burst", "mood": "high_energy",
     "base": [(0.0, (8, 8, 8)), (1.0, (1, 1, 1))],
     "lights": [(0.5, 0.5, 700, (255, 255, 220), 0.25)]},
    {"name": "corner_glow", "mood": "professional",
     "base": [(0.0, (8, 10, 15)), (1.0, (2, 3, 5))],
     "lights": [(0.1, 0.1, 600, (180, 200, 240), 0.15), (0.9, 0.9, 400, (200, 180, 240), 0.10)]},
]


def generate_radial_burst(theme: dict, seed: int, dest: Path) -> dict:
    rng = np.random.RandomState(seed)
    arr = _multi_stop_gradient(H, W, theme["base"])

    for lx, ly, radius, color, intensity in theme["lights"]:
        blob = _elliptical_blob(H, W, lx * W, ly * H, radius, radius * 0.8, intensity)
        for ch in range(3):
            arr[:, :, ch] += blob * color[ch]

    # Radial rays from primary light source
    primary = theme["lights"][0]
    cx, cy = primary[0] * W, primary[1] * H
    color = primary[3]
    n_rays = rng.randint(12, 24)
    ray_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ray_img)
    for i in range(n_rays):
        angle = (2 * math.pi / n_rays) * i + rng.uniform(-0.1, 0.1)
        length = rng.randint(300, 800)
        ex = int(cx + length * math.cos(angle))
        ey = int(cy + length * math.sin(angle))
        alpha = rng.randint(5, 18)
        rd.line([(int(cx), int(cy)), (ex, ey)], fill=(*color, alpha), width=rng.randint(1, 3))
    ray_img = ray_img.filter(ImageFilter.GaussianBlur(radius=8))

    img = _to_image(arr, seed).convert("RGBA")
    img = Image.alpha_composite(img, ray_img)
    img.convert("RGB").save(dest, "JPEG", quality=93)

    return {"category": "radial_burst", "mood": theme["mood"],
            "accent": list(theme["lights"][0][3]), "name": theme["name"]}


# ===========================================================================
# CATEGORY 7: PROCEDURAL MARBLE TEXTURES (4 variants)
# ===========================================================================

MARBLE_THEMES = [
    {"name": "black_gold_marble", "mood": "luxury",
     "base_color": (8, 8, 10), "vein_color": (180, 150, 60),
     "turbulence": 5.0, "octaves": 4},
    {"name": "dark_jade", "mood": "wealth",
     "base_color": (5, 15, 10), "vein_color": (60, 180, 100),
     "turbulence": 4.0, "octaves": 3},
    {"name": "midnight_silver", "mood": "professional",
     "base_color": (10, 12, 15), "vein_color": (160, 170, 185),
     "turbulence": 6.0, "octaves": 4},
    {"name": "crimson_onyx", "mood": "dramatic",
     "base_color": (12, 5, 5), "vein_color": (180, 60, 50),
     "turbulence": 5.5, "octaves": 3},
]


def generate_marble(theme: dict, seed: int, dest: Path) -> dict:
    # Generate layered noise for marble veins
    turb = np.zeros((H, W), dtype=np.float64)
    for octave in range(theme["octaves"]):
        scale = 16 * (2 ** octave)
        amplitude = 1.0 / (1.5 ** octave)
        noise = _noise_layer(W, H, scale=max(4, 256 // scale), seed=seed + octave)
        turb += noise * amplitude

    # Normalize turbulence to 0-1
    turb = (turb - turb.min()) / (turb.max() - turb.min() + 1e-8)

    # Create marble vein pattern
    X = np.linspace(0, 1, W)[np.newaxis, :].repeat(H, axis=0)
    vein = np.sin(X * 12 + turb * theme["turbulence"])
    vein = (vein + 1) / 2  # 0-1 range

    # Sharpen veins
    vein = np.power(vein, 0.6)

    # Color mapping
    base = np.array(theme["base_color"], dtype=np.float64)
    vein_c = np.array(theme["vein_color"], dtype=np.float64)

    arr = np.zeros((H, W, 3), dtype=np.float64)
    for ch in range(3):
        arr[:, :, ch] = base[ch] * (1 - vein * 0.4) + vein_c[ch] * vein * 0.4

    # Add subtle variation
    variation = _noise_layer(W, H, scale=64, seed=seed + 100)
    for ch in range(3):
        arr[:, :, ch] += variation * 8 - 4

    img = _to_image(arr, seed)
    img.convert("RGB").save(dest, "JPEG", quality=93)
    return {"category": "marble_texture", "mood": theme["mood"],
            "accent": list(theme["vein_color"]), "name": theme["name"]}


# ===========================================================================
# CATEGORY 8: DATA VISUALIZATION AESTHETICS (5 variants)
# ===========================================================================

DATAVIZ_THEMES = [
    {"name": "candlestick", "type": "candles", "mood": "wealth",
     "base": [(0.0, (5, 8, 15)), (1.0, (1, 2, 5))], "accent": (50, 255, 120)},
    {"name": "network_graph", "type": "network", "mood": "tech",
     "base": [(0.0, (8, 5, 18)), (1.0, (2, 1, 6))], "accent": (0, 200, 255)},
    {"name": "heatmap_grid", "type": "heatmap", "mood": "professional",
     "base": [(0.0, (8, 8, 12)), (1.0, (2, 2, 4))], "accent": (255, 100, 50)},
    {"name": "scatter_trend", "type": "scatter", "mood": "professional",
     "base": [(0.0, (5, 8, 15)), (1.0, (1, 2, 5))], "accent": (100, 200, 255)},
    {"name": "waveform", "type": "wave", "mood": "dramatic",
     "base": [(0.0, (10, 5, 15)), (1.0, (3, 1, 5))], "accent": (255, 80, 180)},
]


def generate_data_viz(theme: dict, seed: int, dest: Path) -> dict:
    rng = random.Random(seed)
    arr = _multi_stop_gradient(H, W, theme["base"])
    img = _to_image(arr, seed).convert("RGBA")
    draw = ImageDraw.Draw(img)
    accent = theme["accent"]
    vtype = theme["type"]

    if vtype == "candles":
        n = rng.randint(20, 35)
        cw = int(W * 0.7 / n)
        start_x = int(W * 0.15)
        base_price = 100
        for i in range(n):
            change = rng.uniform(-8, 10)
            o = base_price
            c = base_price + change
            hi = max(o, c) + rng.uniform(0, 5)
            lo = min(o, c) - rng.uniform(0, 5)
            base_price = c

            x = start_x + i * (cw + 3)
            scale_y = H * 0.005
            cy_base = H * 0.5

            y_o = int(cy_base - o * scale_y)
            y_c = int(cy_base - c * scale_y)
            y_h = int(cy_base - hi * scale_y)
            y_l = int(cy_base - lo * scale_y)

            is_green = c >= o
            color = (50, 200, 100, 35) if is_green else (200, 60, 60, 35)
            # Wick
            draw.line([(x + cw // 2, y_h), (x + cw // 2, y_l)], fill=color, width=1)
            # Body
            draw.rectangle([(x, min(y_o, y_c)), (x + cw, max(y_o, y_c))], fill=color)

    elif vtype == "network":
        nodes = [(rng.randint(80, W - 80), rng.randint(80, H - 80)) for _ in range(35)]
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                dist = math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1])
                if dist < 250:
                    alpha = int(max(3, 15 * (1 - dist / 250)))
                    draw.line([nodes[i], nodes[j]], fill=(*accent, alpha), width=1)
        for x, y in nodes:
            r = rng.randint(4, 10)
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(*accent, rng.randint(20, 50)))

    elif vtype == "heatmap":
        cols, rows = 16, 9
        cell_w = W // cols
        cell_h = H // rows
        noise_arr = _noise_layer(W, H, scale=32, seed=seed)
        for r in range(rows):
            for c in range(cols):
                ny = min(r * cell_h + cell_h // 2, H - 1)
                nx = min(c * cell_w + cell_w // 2, W - 1)
                val = noise_arr[ny, nx]
                # Cool to warm palette
                red = int(val * accent[0])
                green = int((1 - abs(val - 0.5) * 2) * accent[1])
                blue = int((1 - val) * accent[2])
                alpha = int(15 + val * 30)
                x1, y1 = c * cell_w + 2, r * cell_h + 2
                x2, y2 = (c + 1) * cell_w - 2, (r + 1) * cell_h - 2
                draw.rectangle([(x1, y1), (x2, y2)], fill=(red, green, blue, alpha))

    elif vtype == "scatter":
        n = rng.randint(120, 250)
        for _ in range(n):
            x = rng.randint(100, W - 100)
            y = int(H * 0.7 - (x / W) * H * 0.4 + rng.gauss(0, 60))
            y = max(50, min(H - 50, y))
            r = rng.randint(2, 6)
            alpha = rng.randint(15, 45)
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(*accent, alpha))

    elif vtype == "wave":
        cy = H // 2
        points_top = []
        points_bot = []
        for x in range(0, W, 2):
            t = x / W
            y = (math.sin(t * 8) * 80 + math.sin(t * 15) * 40 +
                 math.sin(t * 23) * 20 + math.sin(t * 3) * 60)
            points_top.append((x, int(cy + y)))
            points_bot.append((x, int(cy - y * 0.6)))

        if len(points_top) > 1:
            draw.line(points_top, fill=(*accent, 40), width=3)
            draw.line(points_bot, fill=(*accent, 20), width=2)

    img.convert("RGB").save(dest, "JPEG", quality=93)
    return {"category": "data_viz", "mood": theme["mood"], "accent": list(accent),
            "name": theme["name"]}


# ===========================================================================
# CATEGORY 9: CINEMATIC LIGHT LEAKS (4 variants)
# ===========================================================================

LIGHTLEAK_THEMES = [
    {"name": "amber_leak", "mood": "warm",
     "base": [(0.0, (5, 4, 3)), (1.0, (1, 1, 0))],
     "blobs": [(0.15, 0.4, 350, 250, (255, 180, 50), 0.3),
               (0.85, 0.3, 300, 200, (255, 120, 30), 0.2)]},
    {"name": "neon_bleed", "mood": "tech",
     "base": [(0.0, (5, 3, 12)), (1.0, (1, 0, 4))],
     "blobs": [(0.1, 0.5, 400, 300, (0, 200, 255), 0.25),
               (0.9, 0.6, 350, 250, (255, 50, 200), 0.2)]},
    {"name": "sunrise_flare", "mood": "aspirational",
     "base": [(0.0, (3, 5, 15)), (0.7, (8, 6, 5)), (1.0, (2, 1, 0))],
     "blobs": [(0.5, 0.85, 600, 200, (255, 150, 50), 0.35),
               (0.6, 0.9, 400, 150, (255, 200, 80), 0.2)]},
    {"name": "cool_haze", "mood": "professional",
     "base": [(0.0, (8, 10, 18)), (1.0, (2, 3, 6))],
     "blobs": [(0.3, 0.3, 500, 350, (150, 200, 255), 0.2),
               (0.7, 0.7, 400, 300, (200, 180, 255), 0.15)]},
]


def generate_light_leak(theme: dict, seed: int, dest: Path) -> dict:
    arr = _multi_stop_gradient(H, W, theme["base"])

    for bx, by, sx, sy, color, intensity in theme["blobs"]:
        blob = _elliptical_blob(H, W, bx * W, by * H, sx, sy, intensity)
        for ch in range(3):
            arr[:, :, ch] += blob * color[ch]

    # Horizontal lens streaks
    rng = np.random.RandomState(seed)
    for _ in range(rng.randint(2, 5)):
        y = rng.randint(int(H * 0.2), int(H * 0.8))
        streak = np.zeros((H, W), dtype=np.float64)
        for dy in range(-8, 9):
            if 0 <= y + dy < H:
                streak[y + dy, :] = np.exp(-abs(dy) / 3.0) * 0.15
        # Taper edges
        taper = np.ones(W, dtype=np.float64)
        edge = W // 6
        taper[:edge] = np.linspace(0, 1, edge)
        taper[-edge:] = np.linspace(1, 0, edge)
        streak *= taper[np.newaxis, :]

        color = theme["blobs"][0][4]
        for ch in range(3):
            arr[:, :, ch] += streak * color[ch]

    img = _to_image(arr, seed)
    img = img.filter(ImageFilter.GaussianBlur(radius=3))
    img.convert("RGB").save(dest, "JPEG", quality=93)

    return {"category": "light_leak", "mood": theme["mood"],
            "accent": list(theme["blobs"][0][4]), "name": theme["name"]}


# ===========================================================================
# MASTER GENERATOR
# ===========================================================================

ALL_GENERATORS = [
    ("gradient", GRADIENT_THEMES, generate_luxury_gradient),
    ("geometric", GEOMETRIC_VARIANTS, generate_geometric),
    ("cityscape", CITYSCAPE_THEMES, generate_cityscape),
    ("wealth_symbol", WEALTH_THEMES, generate_wealth_symbols),
    ("particle_field", PARTICLE_THEMES, generate_particle_field),
    ("radial_burst", RADIAL_THEMES, generate_radial_burst),
    ("marble_texture", MARBLE_THEMES, generate_marble),
    ("data_viz", DATAVIZ_THEMES, generate_data_viz),
    ("light_leak", LIGHTLEAK_THEMES, generate_light_leak),
]


def generate_all_backgrounds(output_dir: Path, force: bool = False) -> list[Path]:
    """
    Generate all 44 backgrounds and write a manifest file.

    Returns list of generated image paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    paths = []
    idx = 0

    for category_name, themes, gen_func in ALL_GENERATORS:
        for ti, theme in enumerate(themes):
            name = theme["name"]
            dest = output_dir / f"bg_{idx:02d}_{name}.jpg"

            if dest.exists() and dest.stat().st_size > 10_000 and not force:
                print(f"  [{idx + 1:02d}/44] Cached: {dest.name}")
                # Load existing manifest entry if possible
                manifest[dest.stem] = {
                    "category": category_name,
                    "mood": theme.get("mood", "neutral"),
                    "accent": list(theme.get("accent", theme.get("vein_color", (255, 255, 255)))),
                    "name": name,
                    "index": idx,
                }
                paths.append(dest)
                idx += 1
                continue

            print(f"  [{idx + 1:02d}/44] Generating: {name} ({category_name})")
            try:
                meta = gen_func(theme, seed=idx * 7 + 42, dest=dest)
                meta["index"] = idx
                manifest[dest.stem] = meta
                paths.append(dest)
            except Exception as e:
                print(f"    WARNING: Failed to generate {name}: {e}")
            idx += 1

    # Write manifest
    manifest_path = output_dir / "bg_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n  Manifest: {manifest_path}")
    print(f"  Total: {len(paths)} backgrounds across {len(ALL_GENERATORS)} categories")

    return paths


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    import argparse
    import time

    p = argparse.ArgumentParser(description="Generate cinematic backgrounds")
    p.add_argument("--output", default=r"C:\money-machine\assets\backgrounds",
                   help="Output directory")
    p.add_argument("--force", action="store_true", help="Regenerate all backgrounds")
    args = p.parse_args()

    t0 = time.time()
    paths = generate_all_backgrounds(Path(args.output), force=args.force)
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")

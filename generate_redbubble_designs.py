#!/usr/bin/env python3
"""
Generate Redbubble-ready quote designs for the finance/wealth niche.
Output: 4500x5400 PNG files (transparent background) suitable for all Redbubble products.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap

OUTPUT_DIR = Path(r"C:\money-machine\output\redbubble")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path(r"C:\Windows\Fonts")

# Design specs
W, H = 4500, 5400

# Color palettes: (background, text_primary, text_accent, text_sub)
PALETTES = [
    {"name": "dark_gold",    "bg": (15, 15, 20),     "primary": (212, 175, 55),  "accent": (255, 255, 255), "sub": (160, 160, 160)},
    {"name": "navy_white",   "bg": (10, 25, 60),     "primary": (255, 255, 255), "accent": (100, 180, 255), "sub": (180, 200, 230)},
    {"name": "forest_cream", "bg": (20, 50, 30),     "primary": (245, 235, 200), "accent": (150, 220, 120), "sub": (180, 210, 160)},
    {"name": "slate_coral",  "bg": (35, 40, 55),     "primary": (255, 120, 100), "accent": (255, 255, 255), "sub": (160, 165, 185)},
    {"name": "cream_black",  "bg": (245, 240, 230),  "primary": (20, 20, 20),    "accent": (150, 50, 30),   "sub": (80, 80, 80)},
]

DESIGNS = [
    {
        "id": "01_compound_interest",
        "palette": "dark_gold",
        "headline": "COMPOUND\nINTEREST",
        "sub": "The 8th Wonder\nof the World",
        "tagline": "INVEST EARLY. INVEST OFTEN.",
    },
    {
        "id": "02_pay_yourself_first",
        "palette": "navy_white",
        "headline": "PAY\nYOURSELF\nFIRST",
        "sub": "Then pay everyone else",
        "tagline": "THE FIRST RULE OF WEALTH",
    },
    {
        "id": "03_time_in_market",
        "palette": "forest_cream",
        "headline": "TIME IN\nTHE MARKET",
        "sub": "beats timing\nthe market",
        "tagline": "STAY THE COURSE",
    },
    {
        "id": "04_financial_freedom",
        "palette": "dark_gold",
        "headline": "FINANCIAL\nFREEDOM",
        "sub": "is not a dream —\nit's a decision",
        "tagline": "START TODAY",
    },
    {
        "id": "05_passive_income",
        "palette": "slate_coral",
        "headline": "MAKE MONEY\nWHILE\nYOU SLEEP",
        "sub": "Build once.\nEarn forever.",
        "tagline": "PASSIVE INCOME IS THE GOAL",
    },
    {
        "id": "06_invest_yourself",
        "palette": "cream_black",
        "headline": "INVEST IN\nYOURSELF\nFIRST",
        "sub": "Best ROI\nyou'll ever get",
        "tagline": "KNOWLEDGE COMPOUNDS TOO",
    },
    {
        "id": "07_debt_free",
        "palette": "navy_white",
        "headline": "DEBT\nFREE",
        "sub": "Not a lifestyle —\na launchpad",
        "tagline": "ZERO DEBT. INFINITE POTENTIAL.",
    },
    {
        "id": "08_multiple_streams",
        "palette": "forest_cream",
        "headline": "MULTIPLE\nSTREAMS",
        "sub": "One job is\none risk",
        "tagline": "DIVERSIFY YOUR INCOME",
    },
    {
        "id": "09_discipline_wealth",
        "palette": "dark_gold",
        "headline": "DISCIPLINE\nBUILDS\nWEALTH",
        "sub": "Motivation fades.\nHabits stay.",
        "tagline": "SHOW UP EVERY DAY",
    },
    {
        "id": "10_1percent_better",
        "palette": "slate_coral",
        "headline": "1% BETTER\nEVERY\nDAY",
        "sub": "365 days later:\n37x improvement",
        "tagline": "ATOMIC HABITS WIN",
    },
]


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def draw_centered_text(draw, text, y, font, color, width=W, line_spacing=1.15):
    """Draw centered text, return bottom Y."""
    lines = text.split("\n")
    line_h = font.getbbox("A")[3]
    total_h = len(lines) * line_h * line_spacing
    cur_y = y
    for line in lines:
        bb = font.getbbox(line)
        lw = bb[2] - bb[0]
        x = (width - lw) // 2
        draw.text((x, cur_y), line, font=font, fill=color)
        cur_y += line_h * line_spacing
    return cur_y


def draw_divider(draw, y, color, width=W, thickness=6, length=600):
    x0 = (width - length) // 2
    draw.rectangle([x0, y, x0 + length, y + thickness], fill=color)


def measure_block_height(d, fonts):
    """Estimate total content height to allow vertical centering."""
    f_headline, f_sub, f_tagline = fonts
    lh_head = f_headline.getbbox("A")[3]
    lh_sub  = f_sub.getbbox("A")[3]
    lh_tag  = f_tagline.getbbox("A")[3]

    n_head = len(d["headline"].split("\n"))
    n_sub  = len(d["sub"].split("\n"))

    h = (n_head * lh_head * 1.1 +   # headline lines
         80 +                         # gap before divider
         6 +                          # divider thickness
         80 +                         # gap after divider
         n_sub * lh_sub * 1.3 +      # sub lines
         120 +                        # gap before bottom divider
         4 +                          # bottom divider
         70 +                         # gap before tagline
         lh_tag)                      # tagline
    return int(h)


def generate_design(d: dict):
    palette = next(p for p in PALETTES if p["name"] == d["palette"])

    img = Image.new("RGBA", (W, H), (*palette["bg"], 255))
    draw = ImageDraw.Draw(img)

    # Fonts
    f_headline = load_font("RockwellNova-ExtraBold.ttf", 420)
    f_sub      = load_font("GeorgiaPro-SemiBold.ttf",    210)
    f_tagline  = load_font("ArialNovaCond-Bold.ttf",     140)
    fonts = (f_headline, f_sub, f_tagline)

    # Vertically center the content block
    content_h = measure_block_height(d, fonts)
    y = max(400, (H - content_h) // 2)

    # Headline
    y = draw_centered_text(draw, d["headline"], y, f_headline, palette["primary"], line_spacing=1.1)
    y += 80

    # Divider
    draw_divider(draw, y, palette["accent"])
    y += 86

    # Sub text
    y = draw_centered_text(draw, d["sub"], y, f_sub, palette["accent"], line_spacing=1.3)
    y += 120

    # Bottom divider
    draw_divider(draw, y, palette["sub"], length=300, thickness=4)
    y += 74

    # Tagline
    draw_centered_text(draw, d["tagline"], y, f_tagline, palette["sub"])

    # Save
    outpath = OUTPUT_DIR / f"{d['id']}.png"
    img.save(str(outpath), "PNG")
    print(f"  Saved: {outpath.name}  ({img.size[0]}x{img.size[1]})")
    return outpath


def main():
    print(f"Generating {len(DESIGNS)} Redbubble designs -> {OUTPUT_DIR}")
    for d in DESIGNS:
        generate_design(d)
    print(f"\nDone. {len(DESIGNS)} designs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

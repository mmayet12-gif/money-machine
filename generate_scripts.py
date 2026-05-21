#!/usr/bin/env python3
"""
Generate 20 personal-finance video scripts.
==========================================

Two modes:

  1. AI mode (recommended) — uses Claude via the Anthropic API to write each script.
     Set the ANTHROPIC_API_KEY environment variable, then:
         python generate_scripts.py

  2. Template mode (offline) — writes solid pre-made scripts so you can run the
     pipeline immediately even without an API key:
         python generate_scripts.py --template

Output: 20 .txt files into C:\\money-machine\\scripts\\
Format matches what run_pipeline.py expects:
    **Title:** ...
    ## Hook
    ...
    ## Context
    ...
    ## Act 1
    ...
    ## Act 2
    ...
    ## Act 3
    ...
    ## Close
    ...
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(r"C:\money-machine\scripts")

# 20 video topics — variety across budgeting, investing, debt, mindset, action
TOPICS = [
    ("01", "The 50/30/20 Budget That Actually Works in 2026"),
    ("02", "Why Your Emergency Fund Is Probably Too Small"),
    ("03", "Index Funds vs Stock Picking: 30 Years of Data"),
    ("04", "How Compound Interest Quietly Makes You Rich"),
    ("05", "The Debt Snowball vs Avalanche: Which Wins?"),
    ("06", "Five Money Habits of People Who Retire Early"),
    ("07", "The Real Cost of Lifestyle Inflation"),
    ("08", "How to Negotiate a Raise Without Sounding Greedy"),
    ("09", "Roth IRA vs Traditional IRA: A Simple Decision Tree"),
    ("10", "The Hidden Tax on Holding Cash Too Long"),
    ("11", "Why High Income Earners Still Go Broke"),
    ("12", "Side Hustles That Actually Generate Real Income"),
    ("13", "The 4% Rule: How Much You Really Need to Retire"),
    ("14", "Credit Score Myths That Are Costing You Money"),
    ("15", "How to Read Your Paycheck Like a Pro"),
    ("16", "The Psychology of Why We Overspend"),
    ("17", "Renting vs Buying: The Math No One Shows You"),
    ("18", "Three Investment Mistakes Beginners Always Make"),
    ("19", "How to Build a Recession-Proof Financial Plan"),
    ("20", "The One-Hour Money System That Changes Everything"),
]


# ---------------------------------------------------------------------------
# Shared script template — used by both modes
# ---------------------------------------------------------------------------
SCRIPT_FORMAT = """**Title:** {title}

## Hook
{hook}

## Context
{context}

## Act 1
{act1}

## Act 2
{act2}

## Act 3
{act3}

## Close
{close}
"""


# ---------------------------------------------------------------------------
# Mode 1: AI generation via Anthropic API
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """You are a senior YouTube scriptwriter for a personal finance channel.

Write a complete script for a 6-8 minute YouTube video titled:
"{title}"

The script must follow this exact structure with these exact section headers,
nothing else (no timestamps, no [VISUAL] tags, no speaker labels):

## Hook
A 2-3 sentence pattern interrupt that grabs attention and states the stakes.
No questions in the first sentence — start with a surprising claim or specific number.

## Context
60-80 words explaining why this matters now, who it applies to, and what
the viewer will learn. Plain spoken English, no jargon.

## Act 1
The first major idea or step. ~150 words. Concrete numbers and one short example.

## Act 2
The second major idea or step. ~150 words. Address a common objection or mistake.

## Act 3
The third major idea or step. ~150 words. The strongest, most actionable point.

## Close
A 60-80 word wrap-up: one-line summary, the single action the viewer should
take today, and a soft call to subscribe. No "smash that like button" energy
— calm and confident.

Rules:
- Conversational, second person ("you").
- US-centric numbers but globally understandable.
- No financial advice disclaimers in the body — those are added later.
- Total target: ~750 words.
- Output ONLY the script, starting with "## Hook". No preamble, no markdown
  fence, no commentary.
"""


def generate_with_api(title: str) -> str:
    """Call Anthropic API. Returns the body (## Hook onwards)."""
    try:
        import anthropic
    except ImportError:
        print("Installing anthropic package...")
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "anthropic"],
            check=True,
        )
        import anthropic

    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": PROMPT_TEMPLATE.format(title=title),
        }],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()

    # Trim anything before "## Hook" just in case
    idx = text.find("## Hook")
    if idx > 0:
        text = text[idx:]
    return text


def parse_ai_output(body: str) -> dict:
    """Pull section bodies out of the AI's output."""
    sections = {}
    pattern = re.compile(
        r"^##\s+(Hook|Context|Act\s*1|Act\s*2|Act\s*3|Close)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    parts = pattern.split(body)
    # parts is like ['', 'Hook', 'text...', 'Context', 'text...', ...]
    for i in range(1, len(parts), 2):
        name = parts[i].lower().replace(" ", "")
        text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[name] = text
    return sections


# ---------------------------------------------------------------------------
# Mode 2: offline templates — generic but solid filler so the pipeline runs
# ---------------------------------------------------------------------------
TEMPLATE_FILLER = {
    "hook": (
        "Here's something most people get wrong about money: "
        "the difference between people who build wealth and people who don't isn't income. "
        "It's a handful of decisions repeated for years. "
        "And one of those decisions is what we're talking about today."
    ),
    "context": (
        "Before we get into the tactics, let's set the stage. "
        "Most personal finance advice is either too vague to use or so detailed it's intimidating. "
        "What I want to do in the next few minutes is give you a clear, simple framework "
        "you can apply this week. No spreadsheets, no jargon, no apps to download. "
        "Just a way of thinking that compounds over time."
    ),
    "act1": (
        "The first thing to understand is that small percentages, given enough time, "
        "become enormous numbers. If you save an extra one hundred dollars a month "
        "and invest it at a seven percent average return, you end up with around "
        "one hundred and twenty thousand dollars in thirty years. "
        "From a hundred bucks a month. "
        "The mistake most people make is dismissing small amounts because they feel small today. "
        "But the math doesn't care how it feels. It just runs."
    ),
    "act2": (
        "The second thing is automation. The single biggest predictor of whether someone "
        "actually saves money is whether the saving happens automatically. "
        "Willpower is a finite resource. Every month you have to consciously decide to save, "
        "you give yourself another chance to not. "
        "Set up a transfer the day after payday. Same amount, same date, every month. "
        "Then forget about it. The boring, mechanical version of you will out-save the motivated version every time."
    ),
    "act3": (
        "The third and most important point is this: simplicity wins. "
        "You do not need a complicated portfolio. You do not need to time the market. "
        "You do not need to read financial news every morning. "
        "A diversified low-cost index fund, held for decades, has beaten the vast majority "
        "of professional money managers. The data on this is overwhelming and it has been "
        "for fifty years. "
        "Pick a strategy that's so boring you can stick with it through a downturn. "
        "That's the one that wins."
    ),
    "close": (
        "So here's your action item for today. Pick one of these three ideas — "
        "compounding, automation, or simplicity — and apply it before the end of the week. "
        "One small change, executed, beats a perfect plan you never start. "
        "If this was useful, hit subscribe so you catch the next one. "
        "I'll see you in the next video."
    ),
}


def make_template_script(title: str) -> str:
    return SCRIPT_FORMAT.format(
        title=title,
        hook=TEMPLATE_FILLER["hook"].replace("today", f"today: {title.lower()}"),
        context=TEMPLATE_FILLER["context"],
        act1=TEMPLATE_FILLER["act1"],
        act2=TEMPLATE_FILLER["act2"],
        act3=TEMPLATE_FILLER["act3"],
        close=TEMPLATE_FILLER["close"],
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--template", action="store_true",
                   help="Use offline templates instead of calling the API")
    p.add_argument("--only", type=int, metavar="N",
                   help="Generate only video N (1-20)")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing scripts")
    args = p.parse_args()

    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    use_api = not args.template
    if use_api and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — falling back to template mode.")
        print("To use Claude for higher-quality scripts:")
        print("  1. Get a key at https://console.anthropic.com/")
        print("  2. Run: setx ANTHROPIC_API_KEY \"sk-ant-...\"")
        print("  3. Open a NEW terminal and re-run this script.\n")
        use_api = False

    succeeded, failed = 0, []

    for idx_str, title in TOPICS:
        idx = int(idx_str)
        if args.only is not None and idx != args.only:
            continue

        out_path = SCRIPTS_DIR / f"{idx_str}_{re.sub(r'[^A-Za-z0-9]+', '_', title)[:60]}.txt"
        if out_path.exists() and not args.force:
            print(f"[{idx_str}/20] Skip (already exists): {out_path.name}")
            succeeded += 1
            continue

        print(f"[{idx_str}/20] Generating: {title}")
        try:
            if use_api:
                body = generate_with_api(title)
                # AI output already has the ## sections — just prepend title line
                content = f"**Title:** {title}\n\n{body}\n"
            else:
                content = make_template_script(title)

            out_path.write_text(content, encoding="utf-8")
            print(f"          ✓ Wrote {out_path.name} ({len(content)} chars)")
            succeeded += 1

            if use_api:
                time.sleep(1.0)  # gentle rate-limit cushion

        except Exception as e:
            print(f"          ✗ FAILED: {type(e).__name__}: {e}")
            failed.append((idx_str, title, str(e)))

    print(f"\n=== {succeeded} succeeded, {len(failed)} failed ===")
    if failed:
        print("\nFailed scripts:")
        for idx, title, err in failed:
            print(f"  {idx}  {title}  →  {err}")
        return 1
    print(f"\nScripts written to: {SCRIPTS_DIR}")
    print("Next: cd to C:\\money-machine and run: python run_pipeline.py --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())

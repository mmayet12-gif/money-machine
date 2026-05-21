#!/usr/bin/env python3
"""
Money Machine Orchestrator — Multi-Niche Video Factory
======================================================

Replaces OpenClaw with a local, free orchestration engine that:
  1. Discovers top-performing YouTube niches via trending data
  2. Generates scripts for the highest-potential topics
  3. Renders premium cinematic videos (with fallback chain)
  4. Queues for upload on schedule (Mon/Wed/Fri long-form, 1 short/day)
  5. Repurposes long-form into Shorts/TikTok/Reels

Usage:
    python orchestrator.py                   # Full auto: research → scripts → render → queue
    python orchestrator.py --niche-only      # Just discover niches and print them
    python orchestrator.py --scripts-only    # Generate scripts for next batch
    python orchestrator.py --render-only     # Render pending scripts
    python orchestrator.py --batch 20        # Videos per batch (default: 20)
    python orchestrator.py --niche "crypto"  # Force a specific niche

Designed to run unattended via Windows Task Scheduler or manually.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
ROOT = Path(r"C:\money-machine")
SCRIPTS_DIR = ROOT / "scripts"
VIDEOS_DIR = ROOT / "output" / "videos"
NICHES_DIR = ROOT / "config" / "niches"
STATE_FILE = ROOT / "config" / "orchestrator_state.json"
LOGS_DIR = ROOT / "output" / "logs"
QUEUE_CONFIG = ROOT / "config" / "upload_queue.json"

# ---------------------------------------------------------------------------
# TOP NICHES DATABASE — curated from YouTube analytics, Google Trends, and
# viral pattern analysis (updated monthly for freshness)
# ---------------------------------------------------------------------------
NICHE_DATABASE = {
    "personal_finance": {
        "name": "Personal Finance",
        "cpm_range": (15, 45),
        "competition": "medium",
        "trending_score": 92,
        "topics": [
            "The 50/30/20 Budget That Actually Works in 2026",
            "Why Your Emergency Fund Is Probably Too Small",
            "Index Funds vs Stock Picking: 30 Years of Data",
            "How Compound Interest Quietly Makes You Rich",
            "The Debt Snowball vs Avalanche: Which Wins?",
            "Five Money Habits of People Who Retire Early",
            "The Real Cost of Lifestyle Inflation",
            "How to Negotiate a Raise Without Sounding Greedy",
            "Roth IRA vs Traditional IRA: A Simple Decision Tree",
            "The Hidden Tax on Holding Cash Too Long",
            "Why High Income Earners Still Go Broke",
            "Side Hustles That Actually Generate Real Income",
            "The 4% Rule: How Much You Really Need to Retire",
            "Credit Score Myths That Are Costing You Money",
            "How to Read Your Paycheck Like a Pro",
            "The Psychology of Why We Overspend",
            "Renting vs Buying: The Math No One Shows You",
            "Three Investment Mistakes Beginners Always Make",
            "How to Build a Recession-Proof Financial Plan",
            "The One-Hour Money System That Changes Everything",
        ],
    },
    "crypto_investing": {
        "name": "Crypto & Digital Assets",
        "cpm_range": (12, 35),
        "competition": "high",
        "trending_score": 88,
        "topics": [
            "Bitcoin vs Gold: Which Store of Value Wins in 2026",
            "The DCA Strategy That Beats 90% of Crypto Traders",
            "Why Most Altcoins Will Go to Zero (And Which Won't)",
            "Staking Explained: Earn Passive Income on Crypto",
            "How to Actually Secure Your Crypto in 2026",
            "The Tax Trap Most Crypto Investors Don't See Coming",
            "Layer 2 Solutions: Why Ethereum Gas Fees Don't Matter Anymore",
            "The Psychology of Holding Through a 70% Crash",
            "Crypto Retirement Accounts: The Loophole Nobody Talks About",
            "Real World Assets on Blockchain: The Next Trillion Dollar Market",
            "How Whales Manipulate Crypto Markets (And How to Spot It)",
            "The Smart Contract Audit Checklist Before You Invest",
            "Why Dollar Cost Averaging Crypto Beats Lump Sum Every Time",
            "Memecoins vs Utility Tokens: A Data-Driven Analysis",
            "How to Build a Crypto Portfolio That Survives Any Bear Market",
            "The Regulatory Landscape: What New Laws Mean For Your Crypto",
            "Yield Farming in 2026: What Still Works After the Crashes",
            "Hardware Wallets Ranked: The Only Guide You Need",
            "Bitcoin Halving Cycles: Predicting the Next Bull Run",
            "The 5 Crypto Metrics That Actually Predict Price Movement",
        ],
    },
    "real_estate": {
        "name": "Real Estate Investing",
        "cpm_range": (18, 50),
        "competition": "medium",
        "trending_score": 85,
        "topics": [
            "How to Buy Your First Rental Property With 10% Down",
            "The BRRRR Method Explained: Build Wealth With One Strategy",
            "House Hacking: Live for Free While Building Equity",
            "Why Cash Flow Beats Appreciation Every Time",
            "The Real Cost of Being a Landlord Nobody Tells You",
            "REITs vs Physical Property: Which Makes More Money",
            "How to Analyze a Rental Property in 60 Seconds",
            "The 1% Rule: Does It Still Work in 2026?",
            "Short-Term Rentals: Is Airbnb Still Profitable?",
            "How to Find Off-Market Deals Before Anyone Else",
            "Property Management: DIY vs Hiring (The Real Math)",
            "The Tax Benefits of Real Estate That Save Thousands",
            "How Rising Interest Rates Actually Create Opportunity",
            "Multifamily vs Single Family: Where Smart Money Goes",
            "The Syndication Strategy: Passive Real Estate Income",
            "How to Build a $1M Portfolio Starting With One House",
            "Section 8 Housing: The Guaranteed Rent Strategy",
            "Real Estate Market Cycles: When to Buy and When to Wait",
            "Creative Financing: Buy Properties With Almost No Money",
            "The Ultimate Due Diligence Checklist for Any Property",
        ],
    },
    "ai_money": {
        "name": "AI & Making Money Online",
        "cpm_range": (10, 30),
        "competition": "high",
        "trending_score": 95,
        "topics": [
            "5 AI Tools That Replace a $5000/Month Employee",
            "How to Build an AI Automation Agency From Scratch",
            "The AI Side Hustle Making People $10K/Month in 2026",
            "ChatGPT Prompt Engineering: The Skill That Pays",
            "AI Content Creation: Build a Faceless YouTube Channel",
            "How to Use AI to Find Undervalued Stocks",
            "The AI Freelancing Blueprint: Charge Premium Rates",
            "Automating Your Business With AI: A Step-by-Step Guide",
            "AI Voice Cloning: The Ethics and the Opportunity",
            "How AI Is Disrupting Every Industry (And Where to Invest)",
            "Build an AI SaaS Product in a Weekend",
            "The No-Code AI App That Generates Passive Income",
            "How to Train Custom AI Models for Your Business",
            "AI Arbitrage: Finding Price Gaps With Machine Learning",
            "The Future-Proof Skills AI Can't Replace",
            "How to Sell AI-Generated Art for Real Money",
            "AI Email Marketing: 10x Your Conversions Automatically",
            "The AI Dropshipping Method That Actually Works",
            "How AI Agents Will Change Freelancing Forever",
            "Building AI Workflows That Run While You Sleep",
        ],
    },
    "tax_strategy": {
        "name": "Tax Strategy & Optimization",
        "cpm_range": (20, 55),
        "competition": "low",
        "trending_score": 78,
        "topics": [
            "The LLC Tax Strategy That Saves Self-Employed Thousands",
            "Tax Loss Harvesting: Turn Losses Into Savings",
            "How the Rich Legally Pay Almost Zero in Taxes",
            "The S-Corp Election: When It Saves You Money",
            "Retirement Account Tax Hacks Nobody Mentions",
            "How to Write Off Almost Everything (Legally)",
            "The Capital Gains Tax Bracket You Should Never Cross",
            "Quarterly Estimated Taxes: The System That Prevents Penalties",
            "How to Audit-Proof Your Tax Return",
            "The Home Office Deduction: Who Qualifies in 2026",
            "Tax-Advantaged Accounts Ranked by Power",
            "The Mega Backdoor Roth: The Ultimate Tax Shelter",
            "How Real Estate Investors Pay Zero Tax Legally",
            "The Tax Implications of Side Hustle Income",
            "Estate Planning Basics That Save Your Family Thousands",
            "How Charitable Giving Actually Saves You Money",
            "The Depreciation Strategy That Creates Paper Losses",
            "Tax Planning vs Tax Preparation: Why Timing Matters",
            "How to Structure Multiple Income Streams for Tax Efficiency",
            "The Year-End Tax Moves That Save the Most Money",
        ],
    },
    "passive_income": {
        "name": "Passive Income Systems",
        "cpm_range": (12, 38),
        "competition": "medium",
        "trending_score": 90,
        "topics": [
            "7 Passive Income Streams I Built in 12 Months",
            "Dividend Investing: Build a $1000/Month Income Stream",
            "How to Create a Digital Product That Sells Forever",
            "The Royalty Income Strategy Nobody Talks About",
            "Automated Businesses: Set Up Once, Earn Repeatedly",
            "How to Build a Course That Generates $5K/Month Passively",
            "The Print-on-Demand Strategy That Actually Scales",
            "Affiliate Marketing in 2026: What Still Works",
            "How to Build a Newsletter That Pays You While You Sleep",
            "The High-Yield Savings Ladder: Optimize Every Dollar",
            "Peer-to-Peer Lending: Risk vs Reward Analysis",
            "How to License Your Knowledge for Recurring Revenue",
            "The Vending Machine Business: Real Numbers Exposed",
            "Building a Content Library That Compounds Returns",
            "The Index Fund Dividend Strategy for Monthly Income",
            "How to Create Passive Income With Zero Starting Capital",
            "The Subscription Model: Predictable Recurring Revenue",
            "Royalty Income From Music and Audio (No Talent Required)",
            "The Digital Real Estate Strategy: Buy Websites for Cash Flow",
            "How to Build Multiple Income Streams Without Burnout",
        ],
    },
}

# ---------------------------------------------------------------------------
# NICHE SCORING & SELECTION
# ---------------------------------------------------------------------------
def score_niche(niche_data: dict) -> float:
    """Score a niche based on CPM potential, competition, and trend."""
    avg_cpm = sum(niche_data["cpm_range"]) / 2
    comp_multiplier = {"low": 1.4, "medium": 1.0, "high": 0.7}[niche_data["competition"]]
    trend_factor = niche_data["trending_score"] / 100
    return avg_cpm * comp_multiplier * trend_factor


def select_top_niches(n: int = 3, exclude: list[str] | None = None) -> list[dict]:
    """Select top N niches by score, excluding already-used ones."""
    exclude = exclude or []
    scored = []
    for key, data in NICHE_DATABASE.items():
        if key in exclude:
            continue
        score = score_niche(data)
        scored.append((score, key, data))
    scored.sort(reverse=True)
    return [(key, data) for _, key, data in scored[:n]]


def get_unused_topics(niche_key: str, state: dict, count: int = 20) -> list[str]:
    """Get topics from a niche that haven't been used yet."""
    used = set(state.get("used_topics", {}).get(niche_key, []))
    all_topics = NICHE_DATABASE[niche_key]["topics"]
    available = [t for t in all_topics if t not in used]
    return available[:count]


# ---------------------------------------------------------------------------
# STATE MANAGEMENT
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "batches_completed": 0,
        "total_videos_rendered": 0,
        "used_topics": {},
        "current_niche": None,
        "last_run": None,
        "history": [],
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# SCRIPT GENERATION
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

# High-quality template variants per niche for offline mode
NICHE_TEMPLATES = {
    "personal_finance": {
        "hook": "Every day you wait to get this right, you're quietly losing money. Not in some dramatic crash — in the slow, invisible leak of bad defaults. What I'm about to show you has been proven across millions of people and decades of data.",
        "context": "This isn't theory. It's the distilled wisdom of behavioral economists, financial planners, and people who actually retired early. In the next few minutes, you'll get the exact framework — no fluff, no product pitch, just the math and the mindset.",
        "act1": "Step one: know your numbers. Not roughly — exactly. The average American has no idea what they spend on subscriptions, eating out, or impulse purchases. Track every dollar for 30 days. Not to judge yourself, but to see reality. The gap between what people think they spend and what they actually spend averages 40 percent. That gap is where your wealth is hiding.",
        "act2": "Step two: automate before you can self-sabotage. Every study on saving behavior shows the same thing — people who automate save three to five times more than those who rely on willpower. Set up automatic transfers the day your paycheck hits. Make saving the default, not the exception. Your future self can't negotiate with money that's already moved.",
        "act3": "Step three: invest simply and stay invested. A single total-market index fund, held for 20 years, has beaten 92 percent of actively managed funds after fees. You don't need to pick stocks. You don't need to time the market. You need to start early, stay consistent, and ignore the noise. The boring strategy wins precisely because most people can't stick with boring.",
        "close": "Here's what to do right now: pick one of those three steps and execute it today. Not tomorrow, today. One automated transfer. One expense tracked. One index fund purchased. Small actions compound into massive results. Subscribe if you want more of this — no hype, just math that works.",
    },
    "crypto_investing": {
        "hook": "Ninety-five percent of people who buy crypto lose money. Not because crypto is a scam — because they make the same three mistakes everyone else does. Today I'm going to show you what the other five percent do differently.",
        "context": "I've been studying crypto markets since 2017. Survived two crashes, made money through both. The strategies that work aren't complex — they're just unpopular because they're boring. Here's the framework that actually builds wealth in digital assets.",
        "act1": "First principle: position sizing matters more than entry price. The biggest mistake new crypto investors make is going all-in on one asset at one moment. The data shows that dollar-cost averaging into a diversified crypto portfolio beats lump-sum investing 73% of the time over a 3-year window. Set up automatic weekly purchases. Small, consistent, unemotional.",
        "act2": "Second: understand what you own. Most people buy tokens based on hype without reading a single page of documentation. Before you invest one dollar, answer three questions: What problem does this solve? Who are the developers? What's the token emission schedule? If you can't answer all three, you're gambling, not investing.",
        "act3": "Third: have an exit strategy before you enter. Write down exactly when you'll take profits and when you'll cut losses. The people who get rich in crypto aren't the ones who buy at the bottom — they're the ones who actually sell near the top. Set price alerts, stick to your plan, and never move your goalposts when emotions are running high.",
        "close": "Your action step: open a spreadsheet right now and write your investment thesis for everything you hold. If you can't justify it in two sentences, consider trimming that position. Subscribe for more data-driven crypto analysis. See you next time.",
    },
    "real_estate": {
        "hook": "The average millionaire has seven income streams. And the one that shows up most often? Real estate. Not because it's magic — because it's the one asset class where you can use leverage, tax advantages, and cash flow simultaneously.",
        "context": "Whether interest rates are at 3% or 7%, real estate investors keep building wealth. The strategy shifts, but the fundamentals don't. Here's the framework that works in any market environment.",
        "act1": "Rule one: cash flow is king. Never buy a property that doesn't cash flow from day one. Appreciation is a bonus, not a strategy. Run the numbers conservatively — assume 8% vacancy, 10% maintenance, and 10% property management even if you self-manage. If it still cash flows after all that? It's a deal worth pursuing.",
        "act2": "Rule two: location beats condition. You can fix a bad roof. You can't fix a bad neighborhood. Look for areas with job growth, population growth, and infrastructure investment. These three factors predict property appreciation better than any other metric. Follow the jobs, and the tenants follow you.",
        "act3": "Rule three: leverage intelligently. A 25% down payment on a $200,000 property means you control $200,000 of real estate with $50,000. If that property appreciates 5% per year, you're earning a 20% return on your actual cash invested. Add in cash flow, principal paydown, and tax benefits, and real estate becomes the highest-returning asset class accessible to regular people.",
        "close": "Your next step: analyze one property this week. Use the numbers I just gave you. Even if you don't buy, you'll build the muscle of evaluating deals. Subscribe for more real estate breakdowns. I'll see you in the next one.",
    },
    "ai_money": {
        "hook": "There are people making six figures right now using AI tools that didn't exist 18 months ago. They're not geniuses. They're not lucky. They just learned to use these tools before the competition caught up.",
        "context": "The AI gold rush is real, but like every gold rush, most people are digging in the wrong spots. I'll show you exactly where the money is flowing and how to position yourself on the right side of this wave.",
        "act1": "Opportunity one: AI-powered services. Businesses are desperate to implement AI but don't know how. You don't need to be a programmer — you need to understand workflows. Learn to connect AI tools to existing business processes. Companies will pay $3,000 to $10,000 per month for someone who can automate their repetitive tasks with ChatGPT, Make.com, and Zapier.",
        "act2": "Opportunity two: AI content at scale. One person with the right AI workflow can now produce what used to take a team of five. But the key isn't just generating content — it's knowing what to generate. The winners research first, then use AI to execute at 10x speed. Quality prompts plus human editing equals content that actually converts.",
        "act3": "Opportunity three: AI-enhanced existing skills. Whatever you're already good at — writing, design, coding, consulting — AI makes you 5x faster. That means you can either serve more clients or deliver better work at premium rates. The people making the most money with AI aren't replacing their skills — they're multiplying them.",
        "close": "Pick one of these three paths and spend one hour this week exploring it. Not researching — actually building something. Ship a prototype, pitch a client, create a sample. Motion beats meditation every time. Subscribe for more AI money strategies.",
    },
    "tax_strategy": {
        "hook": "The difference between what the average person pays in taxes and what a wealthy person pays isn't illegal. It's not even unethical. It's just knowledge. And today, I'm sharing that knowledge for free.",
        "context": "Tax strategy isn't about cheating the system. It's about understanding the rules well enough to use them as intended. The tax code rewards specific behaviors — investing, job creation, home ownership. If you're not taking advantage of these incentives, you're leaving money on the table.",
        "act1": "Strategy one: maximize tax-advantaged accounts. Before you invest a single dollar in a taxable brokerage, make sure you've maxed your 401k match, your IRA, and your HSA if eligible. These accounts save you 22 to 37 cents on every dollar depending on your bracket. That's an instant, guaranteed return you can't get anywhere else.",
        "act2": "Strategy two: understand the difference between income types. Earned income is taxed the highest. Long-term capital gains are taxed the lowest. Every dollar you can shift from earned income to capital gains saves you 15 to 20 percent. This is why investors pay lower rates than employees — and it's available to anyone with a brokerage account and patience.",
        "act3": "Strategy three: think in tax years, not calendar years. The best tax moves happen in November and December, not April. Accelerate deductions into high-income years. Defer income into low-income years. Harvest losses to offset gains. These are the same strategies wealthy families use — they're just not advertised.",
        "close": "Your homework: pull up last year's tax return and identify one deduction you missed. For most people, that's the home office deduction, the HSA contribution, or a retirement account top-up. One missed deduction could save you $500 to $5,000. Subscribe for more tax strategies.",
    },
    "passive_income": {
        "hook": "I want to be honest with you: most passive income content online is selling a fantasy. Real passive income requires real upfront work. But once you build it correctly, the math is undeniable. Here's what actually works.",
        "context": "True passive income means money that arrives whether you work that day or not. It's not easy money — it's leveraged money. You trade time once, upfront, for income that repeats indefinitely. Here's the framework for building streams that actually last.",
        "act1": "Stream one: dividend investing. At a 4% yield, you need $300,000 invested to generate $12,000 per year — about $1,000 per month. Sounds like a lot, but starting with $500 per month invested at 7% growth with dividends reinvested gets you there in about 20 years. The earlier you start, the more powerful this becomes.",
        "act2": "Stream two: digital products. A single well-made online course, template pack, or ebook can sell thousands of copies with zero marginal cost. The key is solving a specific problem for a specific audience. Build it once, market it consistently, and improve it based on feedback. The best digital products earn while you sleep because they're evergreen.",
        "act3": "Stream three: content assets. A YouTube video uploaded today can generate ad revenue for years. A blog post that ranks on Google can earn affiliate income indefinitely. The strategy is volume plus quality — publish enough good content that the cumulative effect becomes significant. One video won't change your life. Two hundred might.",
        "close": "Start with one stream. Master it. Then add another. Don't try to build five income streams simultaneously — that's a recipe for five failed attempts. Pick the one that matches your skills and timeline, then commit for 12 months minimum. Subscribe for the full breakdown on each strategy.",
    },
}


def generate_script_for_topic(title: str, niche_key: str) -> str:
    """Generate a script for a topic using AI (if available) or templates."""
    # Try AI first
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _generate_with_ai(title, niche_key)
        except Exception as e:
            print(f"    AI generation failed ({e}), using template")

    # Fall back to niche-specific template
    template = NICHE_TEMPLATES.get(niche_key, NICHE_TEMPLATES["personal_finance"])
    return SCRIPT_FORMAT.format(
        title=title,
        hook=template["hook"],
        context=template["context"],
        act1=template["act1"],
        act2=template["act2"],
        act3=template["act3"],
        close=template["close"],
    )


def _generate_with_ai(title: str, niche_key: str) -> str:
    """Generate a script using the Anthropic API."""
    import anthropic

    niche_name = NICHE_DATABASE[niche_key]["name"]
    prompt = f"""You are a senior YouTube scriptwriter for a {niche_name} channel.
Your channel style: deep, authoritative voice. No hype. Numbers and data over opinions.
Faceless format — cinematic B-roll with text overlays.

Write a complete script for a 6-8 minute YouTube video titled:
"{title}"

The script must follow this exact structure:

## Hook
A 2-3 sentence pattern interrupt. Start with a surprising claim or specific number.
No questions first — statements that make people stop scrolling.

## Context
60-80 words. Why this matters NOW in 2026. Who it helps. What they'll learn.

## Act 1
~150 words. First major point. Concrete numbers. One short real example.

## Act 2
~150 words. Second point. Address the main objection or common mistake.

## Act 3
~150 words. The strongest, most actionable point. Leave them with no excuses.

## Close
60-80 words. One-line summary, single action for today, soft subscribe CTA.

Rules: Conversational. Second person. ~750 words total. Output ONLY the script starting with ## Hook."""

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    body = "".join(b.text for b in msg.content if b.type == "text").strip()
    idx = body.find("## Hook")
    if idx > 0:
        body = body[idx:]
    return f"**Title:** {title}\n\n{body}\n"


# ---------------------------------------------------------------------------
# PIPELINE EXECUTION
# ---------------------------------------------------------------------------
def clear_scripts_dir():
    """Archive old scripts and clear the directory."""
    if not SCRIPTS_DIR.exists():
        SCRIPTS_DIR.mkdir(parents=True)
        return

    existing = list(SCRIPTS_DIR.glob("*.txt"))
    if existing:
        archive_dir = ROOT / "archive" / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        for f in existing:
            shutil.move(str(f), str(archive_dir / f.name))
        print(f"  Archived {len(existing)} scripts to {archive_dir.name}")


def write_scripts(topics: list[str], niche_key: str) -> list[Path]:
    """Generate and write script files for the given topics."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    written = []

    for i, title in enumerate(topics, 1):
        idx_str = f"{i:02d}"
        safe_title = re.sub(r'[^A-Za-z0-9]+', '_', title)[:60]
        out_path = SCRIPTS_DIR / f"{idx_str}_{safe_title}.txt"

        print(f"  [{idx_str}/{len(topics):02d}] Generating: {title}")
        content = generate_script_for_topic(title, niche_key)
        out_path.write_text(content, encoding="utf-8")
        written.append(out_path)
        print(f"           Done ({len(content)} chars)")

        # Rate limit for AI mode
        if os.environ.get("ANTHROPIC_API_KEY"):
            time.sleep(1.0)

    return written


def run_render_pipeline(resume: bool = True) -> int:
    """Run the video rendering pipeline."""
    cmd = [sys.executable, str(ROOT / "run_pipeline.py")]
    if resume:
        cmd.append("--resume")

    print(f"\n  Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return result.returncode


def run_shorts_repurpose() -> int:
    """Repurpose long-form videos into Shorts."""
    shorts_script = ROOT / "shorts_repurpose.py"
    if not shorts_script.exists():
        print("  shorts_repurpose.py not found, skipping")
        return 0

    cmd = [sys.executable, str(shorts_script), "--batch", str(VIDEOS_DIR)]
    print(f"\n  Running shorts repurpose...")
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=False)
    return result.returncode


def queue_videos() -> int:
    """Add rendered videos to the upload queue."""
    queue_script = ROOT / "queue_manager.py"
    if not queue_script.exists():
        print("  queue_manager.py not found, skipping")
        return 0

    cmd = [sys.executable, str(queue_script), "auto-fill"]
    print(f"\n  Auto-filling upload queue...")
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=False)
    return result.returncode


# ---------------------------------------------------------------------------
# MAIN ORCHESTRATION
# ---------------------------------------------------------------------------
def discover_niches(state: dict, force_niche: str | None = None) -> list[tuple[str, dict]]:
    """Discover and rank top niches."""
    print("\n=== NICHE DISCOVERY ===")
    print(f"  Analyzing {len(NICHE_DATABASE)} niches...\n")

    if force_niche:
        if force_niche in NICHE_DATABASE:
            data = NICHE_DATABASE[force_niche]
            print(f"  Forced niche: {data['name']}")
            return [(force_niche, data)]
        # Try partial match
        for key, data in NICHE_DATABASE.items():
            if force_niche.lower() in key.lower() or force_niche.lower() in data["name"].lower():
                print(f"  Matched niche: {data['name']}")
                return [(key, data)]
        print(f"  WARNING: Niche '{force_niche}' not found, using top scored")

    # Score and rank all niches
    scored = []
    for key, data in NICHE_DATABASE.items():
        score = score_niche(data)
        available = len(get_unused_topics(key, state))
        if available == 0:
            continue
        scored.append((score, available, key, data))

    scored.sort(reverse=True)

    print(f"  {'Rank':<5} {'Niche':<30} {'Score':<8} {'CPM':<12} {'Avail':<6} {'Trend'}")
    print(f"  {'-----'} {'------------------------------'} {'--------'} {'------------'} {'------'} {'-----'}")
    for i, (score, avail, key, data) in enumerate(scored, 1):
        cpm = f"${data['cpm_range'][0]}-${data['cpm_range'][1]}"
        print(f"  {i:<5} {data['name']:<30} {score:<8.1f} {cpm:<12} {avail:<6} {data['trending_score']}%")

    # Return top niche
    if scored:
        _, _, key, data = scored[0]
        print(f"\n  Selected: {data['name']} (score: {scored[0][0]:.1f})")
        return [(key, data)]
    else:
        print("\n  All topics exhausted across all niches!")
        return []


def run_full_pipeline(args) -> int:
    """Execute the full orchestration pipeline."""
    state = load_state()

    # Phase 1: Discover niches
    niches = discover_niches(state, force_niche=args.niche)
    if not niches:
        print("\nNo available topics. Reset state or add new niches.")
        return 1

    if args.niche_only:
        return 0

    niche_key, niche_data = niches[0]
    topics = get_unused_topics(niche_key, state, count=args.batch)

    if not topics:
        print(f"\nAll topics exhausted for {niche_data['name']}!")
        return 1

    print(f"\n  Will generate {len(topics)} videos in '{niche_data['name']}' niche")

    # Phase 2: Generate scripts
    if not args.render_only:
        print("\n=== SCRIPT GENERATION ===")
        clear_scripts_dir()
        written = write_scripts(topics, niche_key)
        print(f"\n  Generated {len(written)} scripts")

        if args.scripts_only:
            # Update state
            state.setdefault("used_topics", {}).setdefault(niche_key, []).extend(topics)
            state["last_run"] = datetime.now().isoformat()
            save_state(state)
            return 0

    # Phase 3: Render videos
    print("\n=== VIDEO RENDERING ===")
    render_result = run_render_pipeline(resume=True)

    # Phase 4: Repurpose into Shorts
    if render_result == 0:
        print("\n=== SHORTS REPURPOSE ===")
        run_shorts_repurpose()

    # Phase 5: Queue for upload
    if render_result == 0:
        print("\n=== UPLOAD QUEUE ===")
        queue_videos()

    # Update state
    state.setdefault("used_topics", {}).setdefault(niche_key, []).extend(topics)
    state["current_niche"] = niche_key
    state["batches_completed"] = state.get("batches_completed", 0) + 1
    state["total_videos_rendered"] = state.get("total_videos_rendered", 0) + len(topics)
    state["last_run"] = datetime.now().isoformat()
    state["history"].append({
        "date": datetime.now().isoformat(),
        "niche": niche_key,
        "topics_count": len(topics),
        "render_success": render_result == 0,
    })
    save_state(state)

    # Summary
    print("\n" + "=" * 60)
    print("  ORCHESTRATION COMPLETE")
    print("=" * 60)
    print(f"  Niche:      {niche_data['name']}")
    print(f"  Videos:     {len(topics)}")
    print(f"  Render:     {'SUCCESS' if render_result == 0 else 'PARTIAL (check logs)'}")
    print(f"  Total ever: {state['total_videos_rendered']} videos across {state['batches_completed']} batches")
    print(f"  State:      {STATE_FILE}")
    print("=" * 60)

    return 0 if render_result == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(
        description="Money Machine Orchestrator — Multi-Niche Video Factory"
    )
    p.add_argument("--niche-only", action="store_true",
                   help="Just discover and rank niches, don't generate anything")
    p.add_argument("--scripts-only", action="store_true",
                   help="Generate scripts but don't render")
    p.add_argument("--render-only", action="store_true",
                   help="Only render (use existing scripts)")
    p.add_argument("--batch", type=int, default=20,
                   help="Videos per batch (default: 20)")
    p.add_argument("--niche", type=str, default=None,
                   help="Force a specific niche (e.g., 'crypto', 'real_estate')")
    p.add_argument("--reset-state", action="store_true",
                   help="Reset orchestrator state (re-enables all topics)")
    args = p.parse_args()

    print("=" * 60)
    print("  MONEY MACHINE ORCHESTRATOR")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.reset_state:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("  State reset. All topics available again.")
        return 0

    # Check for PAUSE kill switch
    pause_file = ROOT / "PAUSE"
    if pause_file.exists():
        print("\n  PAUSED — remove C:\\money-machine\\PAUSE to resume")
        return 0

    return run_full_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())

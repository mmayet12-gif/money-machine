"""
S1-02: Batch YouTube Script Writer
Generates complete retention-optimized scripts for all 30 topics using local Ollama.
Run overnight — expects 4-8 hours on CPU-only machines.

Save to: C:\\money-machine\youtube\s1_02_batch_scriptwriter.py
Run with: python s1_02_batch_scriptwriter.py
"""

import requests
import json
import os
import time
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "llama3.1:8b"          # Change to "mistral:7b" if you want faster (lower quality)
OUTPUT_DIR = r"C:\\money-machine\youtube\scripts"
NICHE      = "personal finance"
DELAY_BETWEEN_SCRIPTS = 5           # seconds pause between scripts (lets CPU cool slightly)

# ── ALL 30 TOPICS ─────────────────────────────────────────────────────────────
TOPICS = [
    {"id": 1,  "title": "7 Money Habits That Keep You Broke",                   "kw": "bad money habits",             "style": "Listicle"},
    {"id": 2,  "title": "How to Save $1,000 in 30 Days (Any Income)",           "kw": "save 1000 fast",               "style": "How-to"},
    {"id": 3,  "title": "Dave Ramsey Baby Steps: Does It Actually Work?",       "kw": "dave ramsey baby steps",       "style": "Educational"},
    {"id": 4,  "title": "Index Funds for Beginners 2026 (Full Guide)",          "kw": "index funds beginners",        "style": "Explainer"},
    {"id": 5,  "title": "Credit Score 800+ Secrets Nobody Tells You",           "kw": "how to get 800 credit score",  "style": "Listicle"},
    {"id": 6,  "title": "Side Hustles That Actually Pay in 2026",               "kw": "side hustles 2026",            "style": "Listicle"},
    {"id": 7,  "title": "What Happens If You Invest $100 Every Month",          "kw": "invest 100 a month",           "style": "Educational"},
    {"id": 8,  "title": "The 50/30/20 Budget: Why It Fails (and Fix)",          "kw": "50 30 20 rule budget",         "style": "Educational"},
    {"id": 9,  "title": "Frugal Living Tips That Don't Feel Like Suffering",    "kw": "frugal living tips",           "style": "Listicle"},
    {"id": 10, "title": "Roth IRA Explained in 10 Minutes",                     "kw": "roth ira explained",           "style": "Explainer"},
    {"id": 11, "title": "Why You're Still Living Paycheck to Paycheck",         "kw": "living paycheck to paycheck",  "style": "Storytelling"},
    {"id": 12, "title": "Best High-Yield Savings Accounts 2026",                "kw": "high yield savings account",   "style": "Listicle"},
    {"id": 13, "title": "Debt Avalanche vs Snowball: The Truth",                "kw": "debt avalanche vs snowball",   "style": "Educational"},
    {"id": 14, "title": "How to Negotiate a Higher Salary (Scripts Included)",  "kw": "how to negotiate salary",      "style": "How-to"},
    {"id": 15, "title": "Passive Income Ideas That Actually Work in 2026",      "kw": "passive income ideas 2026",    "style": "Listicle"},
    {"id": 16, "title": "What a Financial Advisor Won't Tell You",              "kw": "financial advisor secrets",    "style": "Storytelling"},
    {"id": 17, "title": "Emergency Fund: How Much Is Enough?",                  "kw": "emergency fund how much",      "style": "Educational"},
    {"id": 18, "title": "I Tracked Every Penny for 90 Days. Here's What I Found","kw": "expense tracking results",   "style": "Storytelling"},
    {"id": 19, "title": "How to Build Wealth on a $40K Salary",                 "kw": "build wealth low income",      "style": "How-to"},
    {"id": 20, "title": "The Truth About Buy Now Pay Later Apps",               "kw": "buy now pay later dangers",    "style": "Educational"},
    {"id": 21, "title": "HSA: The Most Underused Investment Account",           "kw": "hsa investment account",       "style": "Explainer"},
    {"id": 22, "title": "5 Money Mistakes I Made in My 20s (Don't Copy Me)",   "kw": "money mistakes 20s",           "style": "Storytelling"},
    {"id": 23, "title": "How to Get Out of Debt Fast on Low Income",            "kw": "get out of debt low income",   "style": "How-to"},
    {"id": 24, "title": "Is Buying a Home Still Worth It in 2026?",             "kw": "is buying a house worth it",   "style": "Educational"},
    {"id": 25, "title": "Zero-Based Budgeting: How to Try It This Month",       "kw": "zero based budgeting",         "style": "How-to"},
    {"id": 26, "title": "What I Wish I Knew Before Opening a Brokerage Account","kw": "brokerage account beginners",  "style": "Storytelling"},
    {"id": 27, "title": "The Latte Factor Is a Lie (Here's the Real Problem)",  "kw": "latte factor myth",            "style": "Educational"},
    {"id": 28, "title": "Financial Independence: What It Really Takes",         "kw": "financial independence",       "style": "Educational"},
    {"id": 29, "title": "How Inflation Is Silently Stealing Your Savings",      "kw": "inflation effect on savings",  "style": "Educational"},
    {"id": 30, "title": "The Pay Yourself First Strategy (Step-by-Step)",       "kw": "pay yourself first",           "style": "How-to"},
]

# ── PROMPT TEMPLATE ───────────────────────────────────────────────────────────
def build_prompt(topic):
    return f"""You are an expert YouTube scriptwriter who specializes in faceless channels with 50%+ audience retention.

Write a complete video script for the following:

TITLE: {topic['title']}
TARGET KEYWORD: {topic['kw']}
STYLE: {topic['style']}
TARGET LENGTH: 1,400 words (approximately 10 minutes when spoken at 140 words/minute)
NICHE: {NICHE}

STRICT SCRIPT STRUCTURE:

== HOOK (0:00-0:15) ==
[SOUND EFFECT: whoosh/dramatic sting]
Start with a shocking stat, bold claim, or pattern interrupt. NO "welcome back", NO "in this video", NO "today we're going to". The first sentence must make someone stop scrolling.
[VISUAL: describe compelling opening visual]

== CONTEXT (0:15-0:45) ==
Why this matters RIGHT NOW. Create urgency. Make the viewer feel this is personally relevant to them.
[VISUAL: describe visual]

== MAIN CONTENT (0:45 onward) ==
Use 3-Act structure. Include a [PATTERN INTERRUPT] tag every 60 seconds (change tone, add a surprising stat, pivot perspective). Include [VISUAL: description] every 10-15 seconds. Include [SOUND EFFECT: type] at key moments.

== CLOSE (last 45 seconds) ==
Summarize the 3 biggest takeaways. Open a loop for the next video ("But here's what most people get wrong about X — and that's what I cover in this video..."). End with a strong CTA.

WRITING RULES:
- Write for SPEAKING, not reading. Short sentences. Punchy.
- Use power words: hidden, exposed, truth, shocking, mistake, secret, revealed
- Never say: "In this video", "Welcome back", "Don't forget to like and subscribe" at the start
- Bold key phrases that the voiceover should emphasize using **asterisks**
- Include timestamps in brackets e.g. [1:30]

Write the full script now. Do not truncate. Aim for exactly 1,400 words in the spoken content.

START THE SCRIPT:"""


# ── OLLAMA FUNCTIONS ──────────────────────────────────────────────────────────
def check_ollama():
    try:
        r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": "Say READY", "stream": False}, timeout=30)
        return "response" in r.json()
    except:
        return False


def ask_ollama(prompt, topic_id):
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    try:
        print(f"  Sending to Ollama... (this takes 5-15 min per script on CPU)")
        start = time.time()
        r = requests.post(OLLAMA_URL, json=payload, timeout=1200)  # 20 min max timeout
        elapsed = round(time.time() - start)
        print(f"  Done in {elapsed}s ({elapsed//60}m {elapsed%60}s)")
        return r.json().get("response", "ERROR: empty response")
    except requests.exceptions.Timeout:
        return "ERROR: Timeout — script took too long. Try a shorter prompt or faster model."
    except Exception as e:
        return f"ERROR: {str(e)}"


# ── FILE OPERATIONS ───────────────────────────────────────────────────────────
def save_script(topic, content):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_title = topic['title'][:40].replace(" ", "_").replace("'", "").replace(":", "").replace("/", "-")
    filename = f"S{topic['id']:02d}_{safe_title}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"SCRIPT S1-02 | TOPIC {topic['id']} of 30\n")
        f.write(f"Title:    {topic['title']}\n")
        f.write(f"Keyword:  {topic['kw']}\n")
        f.write(f"Style:    {topic['style']}\n")
        f.write(f"Niche:    {NICHE}\n")
        f.write(f"Generated:{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 70 + "\n\n")
        f.write(content)
        f.write("\n\n" + "=" * 70 + "\n")
        f.write("END OF SCRIPT — Ready for S1-03 (TTS Optimization)\n")

    return filepath


def save_progress_log(completed, failed, total):
    log_path = os.path.join(OUTPUT_DIR, "_progress.json")
    data = {
        "completed": completed,
        "failed": failed,
        "total": total,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "percent_done": round(len(completed) / total * 100, 1)
    }
    with open(log_path, "w") as f:
        json.dump(data, f, indent=2)


def load_progress():
    log_path = os.path.join(OUTPUT_DIR, "_progress.json")
    if os.path.exists(log_path):
        with open(log_path) as f:
            return json.load(f)
    return {"completed": [], "failed": []}


# ── MAIN BATCH RUNNER ─────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  S1-02 BATCH SCRIPT WRITER — ALL 30 TOPICS")
    print(f"  Model: {MODEL} | Niche: {NICHE}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)
    print()

    # Check Ollama
    print("Checking Ollama connection...")
    if not check_ollama():
        print("\nERROR: Ollama is not running.")
        print("Fix: Open a new terminal and run:  ollama serve")
        print("Then run this script again.")
        return
    print("Ollama: OK\n")

    # Load progress (resume support — safe to re-run after interruption)
    progress = load_progress()
    completed_ids = progress.get("completed", [])
    failed_ids    = progress.get("failed", [])

    remaining = [t for t in TOPICS if t["id"] not in completed_ids]

    if completed_ids:
        print(f"Resuming from previous run.")
        print(f"  Already done: {len(completed_ids)}/30")
        print(f"  Remaining:    {len(remaining)}/30\n")
    else:
        print(f"Starting fresh — generating all 30 scripts.\n")
        print("TIP: This will take 4-8 hours on CPU. Leave it running overnight.\n")

    if not remaining:
        print("All 30 scripts already generated! Check your output folder.")
        return

    # Confirm before starting
    ans = input(f"Start generating {len(remaining)} scripts? (y/n): ").strip().lower()
    if ans != 'y':
        print("Cancelled.")
        return

    print()
    session_start = time.time()

    for i, topic in enumerate(remaining):
        print(f"[{len(completed_ids)+i+1}/30] Generating: {topic['title']}")

        prompt  = build_prompt(topic)
        content = ask_ollama(prompt, topic["id"])

        if content.startswith("ERROR"):
            print(f"  FAILED: {content}")
            failed_ids.append(topic["id"])
        else:
            filepath = save_script(topic, content)
            completed_ids.append(topic["id"])
            word_count = len(content.split())
            print(f"  Saved: {os.path.basename(filepath)} ({word_count:,} words)")

        # Save progress after every script (crash-safe)
        save_progress_log(completed_ids, failed_ids, len(TOPICS))

        # Cooldown between scripts
        if i < len(remaining) - 1:
            print(f"  Cooling down {DELAY_BETWEEN_SCRIPTS}s before next script...\n")
            time.sleep(DELAY_BETWEEN_SCRIPTS)

    # Final summary
    elapsed_total = round(time.time() - session_start)
    print()
    print("=" * 60)
    print(f"  BATCH COMPLETE")
    print(f"  Done:   {len(completed_ids)}/30 scripts")
    print(f"  Failed: {len(failed_ids)} scripts {failed_ids if failed_ids else ''}")
    print(f"  Time:   {elapsed_total//3600}h {(elapsed_total%3600)//60}m")
    print(f"  Folder: {OUTPUT_DIR}")
    print("=" * 60)

    if failed_ids:
        print(f"\nTo retry failed scripts, just run this script again.")
        print("It will automatically skip completed ones and retry failed ones.")

    print("\nAll scripts ready for S1-03 (TTS Voiceover Optimization).")
    print("Say NEXT when ready.")


if __name__ == "__main__":
    main()
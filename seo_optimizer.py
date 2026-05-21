#!/usr/bin/env python3
"""
SEO Optimizer — updates all uploaded videos with better titles, descriptions, tags.
Also updates channel description and keywords.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\money-machine")
CONFIG_DIR = ROOT / "config"
TOKEN_FILE_SEO = CONFIG_DIR / "token_seo.json"
CLIENT_SECRET = CONFIG_DIR / "client_secret.json"

SEO_SCOPES = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube",
]


def get_seo_credentials():
    """Get credentials with edit scope, prompting re-auth if needed."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if TOKEN_FILE_SEO.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE_SEO), SEO_SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                TOKEN_FILE_SEO.write_text(creds.to_json(), encoding="utf-8")
                return creds
            except Exception:
                pass
        # Need fresh auth
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SEO_SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_FILE_SEO.write_text(creds.to_json(), encoding="utf-8")
        print("  SEO credentials saved.")

    return creds


def build_seo_service():
    from googleapiclient.discovery import build
    creds = get_seo_credentials()
    return build("youtube", "v3", credentials=creds)

UPLOAD_LOG = ROOT / "logs" / "uploads.log"

# ── Per-niche SEO config ────────────────────────────────────────────────────
NICHE_SEO = {
    "personal_finance": {
        "tags": [
            "personal finance", "money tips", "budgeting", "financial freedom",
            "wealth building", "save money", "invest money", "financial advice 2026",
            "money management", "debt free", "financial independence", "rich habits",
            "Muhammad Mayet", "finance tips", "how to get rich",
        ],
        "category_id": "27",
        "description_footer": (
            "\n\n📌 ABOUT THIS CHANNEL\n"
            "We break down personal finance, investing, and wealth-building strategies "
            "into clear, actionable advice — no jargon, no hype. New video every day.\n\n"
            "👉 Subscribe for daily financial insights: https://youtube.com/@MuhammadMayet\n\n"
            "#PersonalFinance #MoneyTips #FinancialFreedom #WealthBuilding #Investing2026"
        ),
    },
    "passive_income": {
        "tags": [
            "passive income", "passive income ideas 2026", "make money online",
            "side hustle", "financial freedom", "earn money while you sleep",
            "online income", "income streams", "wealth building", "investing",
            "Muhammad Mayet", "money tips", "how to make money",
        ],
        "category_id": "27",
        "description_footer": (
            "\n\n📌 ABOUT THIS CHANNEL\n"
            "Real passive income strategies that actually work in 2026. "
            "No get-rich-quick schemes — just proven methods backed by data.\n\n"
            "👉 Subscribe: https://youtube.com/@MuhammadMayet\n\n"
            "#PassiveIncome #MakeMoneyOnline #SideHustle #FinancialFreedom #Income2026"
        ),
    },
    "investing": {
        "tags": [
            "investing for beginners", "stock market", "index funds", "ETF investing",
            "compound interest", "portfolio", "dividend investing", "wealth building",
            "how to invest", "investment strategy 2026", "financial independence",
            "Muhammad Mayet", "investing tips", "stock market basics",
        ],
        "category_id": "27",
        "description_footer": (
            "\n\n📌 ABOUT THIS CHANNEL\n"
            "Smart investing strategies explained simply. From index funds to dividends, "
            "we cover what actually works for long-term wealth.\n\n"
            "👉 Subscribe: https://youtube.com/@MuhammadMayet\n\n"
            "#Investing #StockMarket #IndexFunds #CompoundInterest #WealthBuilding"
        ),
    },
    "default": {
        "tags": [
            "personal finance", "money tips", "financial freedom", "budgeting",
            "wealth building", "investing", "save money", "financial advice",
            "Muhammad Mayet", "money management", "financial independence",
        ],
        "category_id": "27",
        "description_footer": (
            "\n\n📌 ABOUT THIS CHANNEL\n"
            "Clear, actionable money advice to help you build wealth and achieve "
            "financial freedom. New video every single day.\n\n"
            "👉 Subscribe: https://youtube.com/@MuhammadMayet\n\n"
            "#PersonalFinance #Money #FinancialFreedom #Investing #WealthBuilding"
        ),
    },
}

POWER_PREFIXES = [
    "The TRUTH About", "Why Most People Get", "How to Actually",
    "The REAL", "Science-Backed:", "PROVEN:", "What Nobody Tells You About",
]

DESCRIPTION_HOOKS = [
    "Most people get this completely wrong — here's what the data actually shows.",
    "This single concept has helped thousands of people transform their finances.",
    "If you're serious about financial freedom, you need to understand this.",
    "The math on this is undeniable once you see it laid out clearly.",
    "After researching this for months, here's what we found.",
]


def get_uploaded_videos() -> list[dict]:
    """Read upload log and return list of successfully uploaded videos."""
    if not UPLOAD_LOG.exists():
        return []
    videos = []
    for line in UPLOAD_LOG.read_text(encoding="utf-8").strip().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("result") == "success" and entry.get("video_id"):
                videos.append(entry)
        except json.JSONDecodeError:
            continue
    return videos


def detect_niche(title: str) -> str:
    title_lower = title.lower()
    if any(w in title_lower for w in ["passive", "stream", "royalt", "course", "print", "affiliate", "newsletter"]):
        return "passive_income"
    if any(w in title_lower for w in ["invest", "index fund", "stock", "compound", "dividend", "etf", "roth", "ira", "portfolio"]):
        return "investing"
    return "personal_finance"


def build_optimized_description(title: str, original_desc: str, niche: str) -> str:
    hook = DESCRIPTION_HOOKS[hash(title) % len(DESCRIPTION_HOOKS)]
    footer = NICHE_SEO.get(niche, NICHE_SEO["default"])["description_footer"]

    # Build timestamp block (approximated for ~2.5 min video)
    timestamps = (
        "⏱️ TIMESTAMPS\n"
        "0:00 — Introduction\n"
        "0:20 — The core concept\n"
        "0:55 — Step-by-step breakdown\n"
        "1:45 — Key takeaways\n"
        "2:10 — How to apply this today\n"
    )

    desc = (
        f"{hook}\n\n"
        f"In this video, we cover everything you need to know about: {title.lower()}. "
        f"Whether you're just starting your financial journey or looking to level up, "
        f"this breakdown will give you the exact framework to move forward.\n\n"
        f"{timestamps}\n"
        f"🔔 Turn on notifications so you never miss a video.\n"
        f"{footer}"
    )
    return desc


def optimize_title(title: str) -> str:
    """Keep title but make sure it's punchy — add year if not present."""
    if "2026" not in title and len(title) < 55:
        return f"{title} (2026)"
    return title


def update_channel_branding(service):
    """Update channel description and keywords."""
    print("\nUpdating channel branding...")
    channel_desc = (
        "Clear, actionable financial advice for people serious about building wealth. "
        "We cover budgeting, investing, passive income, taxes, and everything in between — "
        "explained simply, backed by data, and updated for 2026.\n\n"
        "New video every single day. Subscribe and turn on notifications so you never miss one.\n\n"
        "Topics: Personal Finance | Investing | Passive Income | Budgeting | Financial Freedom | "
        "Debt Payoff | Tax Strategy | Wealth Building"
    )
    channel_keywords = (
        "personal finance, money tips, investing, budgeting, financial freedom, "
        "passive income, wealth building, debt free, save money, financial independence, "
        "index funds, compound interest, side hustle, financial advice 2026"
    )
    try:
        service.channels().update(
            part="brandingSettings",
            body={
                "id": "UCdS4vV-8wH7FatLrLUF-tZw",
                "brandingSettings": {
                    "channel": {
                        "description": channel_desc,
                        "keywords": channel_keywords,
                        "defaultLanguage": "en",
                        "country": "ZA",
                    }
                }
            }
        ).execute()
        print("  Channel description updated.")
    except Exception as e:
        print(f"  Channel update failed: {e}")


def optimize_all_videos():
    print("Loading credentials (edit scope)...")
    service = build_seo_service()

    # Update channel branding first
    update_channel_branding(service)

    # Get all uploaded videos
    uploaded = get_uploaded_videos()
    if not uploaded:
        print("No uploaded videos found in log.")
        return

    print(f"\nOptimizing {len(uploaded)} videos...\n")

    for i, entry in enumerate(uploaded):
        video_id = entry["video_id"]
        title = entry["title"]
        niche = detect_niche(title)
        seo = NICHE_SEO.get(niche, NICHE_SEO["default"])

        new_title = optimize_title(title)
        new_desc = build_optimized_description(title, "", niche)
        new_tags = seo["tags"][:30]  # YouTube max 30 tags

        print(f"[{i+1}/{len(uploaded)}] {title[:55]}")
        print(f"  Niche: {niche} | New title: {new_title[:55]}")

        try:
            service.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": {
                        "title": new_title,
                        "description": new_desc,
                        "tags": new_tags,
                        "categoryId": seo["category_id"],
                        "defaultLanguage": "en",
                    }
                }
            ).execute()
            print(f"  Updated.")
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"  FAILED: {e}")
            if "quotaExceeded" in str(e):
                print("  API quota hit — stopping.")
                break
            time.sleep(2)

    print(f"\nSEO optimization complete!")


if __name__ == "__main__":
    optimize_all_videos()

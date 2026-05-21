#!/usr/bin/env python3
"""Generate scripts for ALL niches (120 videos total)."""
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\money-machine")
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(ROOT))
from orchestrator import NICHE_DATABASE, NICHE_TEMPLATES, SCRIPT_FORMAT

# Archive current scripts
existing = list(SCRIPTS_DIR.glob("*.txt"))
if existing:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = ROOT / "archive" / f"batch_{ts}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for f in existing:
        shutil.move(str(f), str(archive_dir / f.name))
    print(f"Archived {len(existing)} old scripts")

SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Generate all scripts across all niches
total = 0
for niche_key, niche_data in NICHE_DATABASE.items():
    template = NICHE_TEMPLATES.get(niche_key, NICHE_TEMPLATES["personal_finance"])
    niche_name = niche_data["name"]
    print(f"\n--- {niche_name} ({len(niche_data['topics'])} topics) ---")

    for i, title in enumerate(niche_data["topics"], 1):
        total += 1
        idx_str = f"{total:03d}"
        safe_title = re.sub(r"[^A-Za-z0-9]+", "_", title)[:55]
        out_path = SCRIPTS_DIR / f"{idx_str}_{safe_title}.txt"

        content = SCRIPT_FORMAT.format(
            title=title,
            hook=template["hook"],
            context=template["context"],
            act1=template["act1"],
            act2=template["act2"],
            act3=template["act3"],
            close=template["close"],
        )
        out_path.write_text(content, encoding="utf-8")
        print(f"  [{idx_str}] {title}")

    print(f"  -> {len(niche_data['topics'])} scripts written for {niche_name}")

print(f"\n{'='*60}")
print(f"  TOTAL: {total} scripts generated across {len(NICHE_DATABASE)} niches")
print(f"  Location: {SCRIPTS_DIR}")
print(f"{'='*60}")

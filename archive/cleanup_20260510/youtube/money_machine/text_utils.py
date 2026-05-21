from __future__ import annotations

import re


MOJIBAKE_REPLACEMENTS = {
    "â€”": "-",
    "â€“": "-",
    "â€™": "'",
    "â€œ": '"',
    "â€": '"',
    "â€¦": "...",
}


def normalize_text(text: str, ascii_only: bool = True) -> str:
    normalized = text
    for source, target in MOJIBAKE_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"\r\n?", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip() + "\n"
    if ascii_only:
        normalized = normalized.encode("ascii", errors="ignore").decode("ascii")
        normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    return normalized


def slugify(value: str) -> str:
    clean = value.lower().strip()
    clean = re.sub(r"[^a-z0-9]+", "-", clean)
    clean = re.sub(r"-{2,}", "-", clean)
    return clean.strip("-") or "item"

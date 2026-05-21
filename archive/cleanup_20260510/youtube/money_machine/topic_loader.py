from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from .config import PipelineConfig
from .types import Topic


class TopicLoadError(ValueError):
    pass


def _coerce_topic(idx: int, row: dict) -> Topic:
    return Topic(
        idx=idx,
        title=str(row.get("title", f"Topic {idx}")).strip(),
        keyword=str(row.get("kw", row.get("keyword", ""))).strip(),
        hook=str(row.get("hook", "")).strip(),
        volume=str(row.get("vol", row.get("volume", "Medium"))).strip() or "Medium",
        monetization=[str(x) for x in (row.get("mon") or row.get("monetization") or [])],
        structure=[str(x) for x in (row.get("struct") or row.get("structure") or [])],
    )


def _parse_topics_html(path: Path) -> List[Topic]:
    if not path.exists():
        raise TopicLoadError(f"HTML topics file not found: {path}")
    raw = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"const\s+topics\s*=\s*(\[[\s\S]*?\]);", raw)
    if not match:
        raise TopicLoadError("Could not find 'const topics = [...]' in HTML file.")
    js_array = match.group(1)
    as_json = re.sub(r"(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1 "\2":', js_array)
    as_json = re.sub(r",\s*([}\]])", r"\1", as_json)
    rows = json.loads(as_json)
    topics = [_coerce_topic(i + 1, row) for i, row in enumerate(rows)]
    if not topics:
        raise TopicLoadError("No topics parsed from HTML file.")
    return topics


def _parse_topics_json(path: Path) -> List[Topic]:
    if not path.exists():
        raise TopicLoadError(f"JSON topics file not found: {path}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise TopicLoadError("JSON topics file must contain a top-level list.")
    topics = [_coerce_topic(i + 1, row) for i, row in enumerate(rows)]
    if not topics:
        raise TopicLoadError("No topics parsed from JSON file.")
    return topics


def _fallback_topics(niche: str, size: int) -> List[Topic]:
    items: List[Topic] = []
    for i in range(1, size + 1):
        items.append(
            Topic(
                idx=i,
                title=f"{niche.title()} Strategy {i}",
                keyword=f"{niche} tips {i}",
                hook=f"One shift can improve your {niche} results this month.",
                volume="Medium",
                monetization=["Ads", "Affiliate"],
                structure=[
                    "Core principle",
                    "Common mistake",
                    "Step-by-step fix",
                    "Action challenge",
                ],
            )
        )
    return items


def load_topics(config: PipelineConfig) -> List[Topic]:
    if config.topics_source.source_type == "inline":
        inline = config.topics_source.inline_topics
        if not inline:
            return _fallback_topics(config.niche, config.batch_size)
        return [_coerce_topic(i + 1, row) for i, row in enumerate(inline[: config.batch_size])]

    if config.topics_source.path:
        try:
            source_path = Path(config.topics_source.path)
            if config.topics_source.source_type == "json":
                topics = _parse_topics_json(source_path)
            else:
                topics = _parse_topics_html(source_path)
            return topics[: config.batch_size]
        except TopicLoadError:
            pass
    return _fallback_topics(config.niche, config.batch_size)

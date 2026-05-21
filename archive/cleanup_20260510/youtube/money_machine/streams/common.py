from __future__ import annotations

from typing import Iterable, List

from ..config import PipelineConfig, StreamConfig
from ..types import GenerationUnit, Topic
from ..text_utils import slugify


def _topic_outline(topic: Topic) -> str:
    bullets = "\n".join([f"- {s}" for s in topic.structure])
    return (
        f"Title: {topic.title}\n"
        f"Keyword: {topic.keyword}\n"
        f"Hook: {topic.hook}\n"
        f"Volume: {topic.volume}\n"
        f"Monetization: {', '.join(topic.monetization)}\n"
        f"Structure:\n{bullets}\n"
    )


def build_units(
    stream: StreamConfig,
    config: PipelineConfig,
    topics: Iterable[Topic],
    prompt_header: str,
    unit_prefix: str,
) -> List[GenerationUnit]:
    units: List[GenerationUnit] = []
    for topic in topics:
        uid = f"{unit_prefix}_{topic.idx:02d}_{slugify(topic.title)[:36]}"
        prompt = (
            f"{prompt_header}\n\n"
            f"NICHE: {config.niche}\n"
            f"TARGET AUDIENCE: {config.target_audience}\n"
            f"TONE: {config.tone}\n"
            f"LANGUAGE: {config.language}\n\n"
            f"{_topic_outline(topic)}\n"
            "Return production-ready output only."
        )
        units.append(
            GenerationUnit(
                unit_id=uid,
                title=topic.title,
                prompt=prompt,
                metadata={"stream_id": stream.stream_id, "keyword": topic.keyword},
            )
        )
    return units

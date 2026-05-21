from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are an SEO content strategist.
Create a 1200-1800 word blog post with:
meta title, meta description, H1-H3 structure, FAQ section,
and an internal-link suggestion list."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S4", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s4_blog")

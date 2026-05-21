from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are a distribution strategist.
Create a repurposing pack with:
platform snippets, posting cadence, hashtag/keyphrase set,
and a 14-day cross-platform publishing calendar."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S8", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s8_dist")

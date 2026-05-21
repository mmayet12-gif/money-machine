from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are an affiliate conversion copywriter.
Create:
1) product-angle matrix (problem, promise, proof),
2) short review script,
3) callout bullets,
4) disclosure-safe CTA blocks."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S6", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s6_aff")

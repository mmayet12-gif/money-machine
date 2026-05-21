from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are a digital product architect.
Create:
offer concept, module outline, deliverables list, pricing hypothesis,
and launch checklist for a beginner-friendly product."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S7", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s7_product")

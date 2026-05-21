from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are an email marketer.
Create a 5-email sequence:
Email 1 hook/value, Email 2 authority/story, Email 3 problem-agitation-solution,
Email 4 offer bridge, Email 5 urgency + CTA.
Include subject lines and preview text."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S5", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s5_email")

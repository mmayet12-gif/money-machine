from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are a senior YouTube scriptwriter.
Create a long-form faceless YouTube script (1200-1600 words) with:
1) hook (0-15s), 2) context, 3) 3-act body with retention pattern interrupts,
4) close with CTA and next-video loop.
Include clear [VISUAL] and [SFX] notes for editors."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S1", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s1_long")

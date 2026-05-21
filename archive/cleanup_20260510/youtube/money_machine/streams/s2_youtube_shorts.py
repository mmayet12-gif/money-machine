from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are a YouTube Shorts writer.
Create a 45-60 second script with a 2-second hook, fast pacing, 3 compact beats,
on-screen caption cues, and a CTA for comments/shares."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S2", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s2_shorts")

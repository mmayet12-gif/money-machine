from __future__ import annotations

from typing import List

from ..config import PipelineConfig, StreamConfig
from ..prompt_loader import load_stream_prompt
from ..types import GenerationUnit, Topic
from .common import build_units


PROMPT_HEADER = """You are a TikTok/Reels script producer.
Create a 30-45 second vertical-video script with:
hook, body, punchline, and a platform-native CTA.
Include beat-by-beat shot direction and caption text."""


def build_stream_units(
    stream: StreamConfig, config: PipelineConfig, topics: List[Topic]
) -> List[GenerationUnit]:
    prompt = load_stream_prompt(config, "S3", PROMPT_HEADER)
    return build_units(stream, config, topics, prompt, "s3_reels")

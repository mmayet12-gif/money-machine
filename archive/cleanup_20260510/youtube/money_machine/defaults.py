from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


KNOWN_STREAMS = [
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6",
    "S7",
    "S8",
]


@dataclass(frozen=True)
class StreamDefault:
    stream_id: str
    name: str
    output_formats: List[str]


STREAM_DEFAULTS: Dict[str, StreamDefault] = {
    "S1": StreamDefault("S1", "YouTube Long-form", ["md", "txt"]),
    "S2": StreamDefault("S2", "YouTube Shorts", ["md", "txt"]),
    "S3": StreamDefault("S3", "TikTok/Reels Scripts", ["md", "txt"]),
    "S4": StreamDefault("S4", "SEO Blog Articles", ["md", "html"]),
    "S5": StreamDefault("S5", "Email Newsletter Sequence", ["md", "txt"]),
    "S6": StreamDefault("S6", "Affiliate Offer Assets", ["md", "txt"]),
    "S7": StreamDefault("S7", "Digital Product Assets", ["md", "txt"]),
    "S8": StreamDefault("S8", "Repurposing/Distribution Pack", ["md", "txt"]),
}


DEFAULT_CONFIG = {
    "pipeline_version": "1.0",
    "model_policy": "local-ollama",
    "niche": "personal finance",
    "target_audience": "working adults 25-45",
    "tone": "clear, practical, motivational",
    "language": "English",
    "output_root": "runs",
    "prompts_root": "prompts",
    "batch_size": 30,
    "checkpointing": True,
    "topics_source": {"type": "json", "path": "data/topics_seed.json"},
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "llama3.1:8b",
        "max_retries": 2,
        "timeouts": {
            "connect_seconds": 10,
            "read_seconds": 600,
        },
    },
    "streams": [
        {
            "id": STREAM_DEFAULTS[sid].stream_id,
            "name": STREAM_DEFAULTS[sid].name,
            "enabled": True,
            "output_formats": STREAM_DEFAULTS[sid].output_formats,
        }
        for sid in KNOWN_STREAMS
    ],
}

from __future__ import annotations

from pathlib import Path

from .config import PipelineConfig


def load_stream_prompt(config: PipelineConfig, stream_id: str, fallback: str) -> str:
    prompts_root = Path(config.prompts_root)
    file_path = prompts_root / f"{stream_id.lower()}.prompt.txt"
    if file_path.exists():
        text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            return text
    return fallback

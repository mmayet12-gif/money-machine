from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .defaults import DEFAULT_CONFIG, KNOWN_STREAMS, STREAM_DEFAULTS


class ConfigError(ValueError):
    pass


@dataclass
class Timeouts:
    connect_seconds: int
    read_seconds: int


@dataclass
class OllamaConfig:
    base_url: str
    model: str
    max_retries: int
    timeouts: Timeouts


@dataclass
class StreamConfig:
    stream_id: str
    name: str
    enabled: bool
    output_formats: List[str]


@dataclass
class TopicsSourceConfig:
    source_type: str
    path: str = ""
    inline_topics: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PipelineConfig:
    pipeline_version: str
    model_policy: str
    niche: str
    target_audience: str
    tone: str
    language: str
    output_root: str
    prompts_root: str
    batch_size: int
    checkpointing: bool
    topics_source: TopicsSourceConfig
    ollama: OllamaConfig
    streams: List[StreamConfig]


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate_streams(raw_streams: List[Dict[str, Any]]) -> List[StreamConfig]:
    if not raw_streams:
        raise ConfigError("Config must include at least one stream.")
    stream_ids = set()
    stream_configs: List[StreamConfig] = []
    for item in raw_streams:
        sid = str(item.get("id", "")).upper().strip()
        if sid not in KNOWN_STREAMS:
            raise ConfigError(f"Unknown stream id '{sid}'. Allowed: {', '.join(KNOWN_STREAMS)}")
        if sid in stream_ids:
            raise ConfigError(f"Duplicate stream id '{sid}' in config.")
        stream_ids.add(sid)
        formats = item.get("output_formats") or STREAM_DEFAULTS[sid].output_formats
        if not isinstance(formats, list) or not formats:
            raise ConfigError(f"stream {sid} requires non-empty output_formats.")
        for fmt in formats:
            if fmt not in {"txt", "md", "html"}:
                raise ConfigError(f"Unsupported output format '{fmt}' in stream {sid}.")
        stream_configs.append(
            StreamConfig(
                stream_id=sid,
                name=str(item.get("name") or STREAM_DEFAULTS[sid].name),
                enabled=bool(item.get("enabled", True)),
                output_formats=formats,
            )
        )
    return stream_configs


def _validate_and_build(data: Dict[str, Any]) -> PipelineConfig:
    model_policy = str(data.get("model_policy", "")).strip()
    if model_policy != "local-ollama":
        raise ConfigError("model_policy must be 'local-ollama' for v1.")

    topics_source_raw = data.get("topics_source", {})
    source_type = str(topics_source_raw.get("type", "html")).strip().lower()
    if source_type not in {"html", "json", "inline"}:
        raise ConfigError("topics_source.type must be either 'html', 'json', or 'inline'.")

    topics_source = TopicsSourceConfig(
        source_type=source_type,
        path=str(topics_source_raw.get("path", "")),
        inline_topics=topics_source_raw.get("inline_topics", []) or [],
    )

    if source_type == "inline" and not isinstance(topics_source.inline_topics, list):
        raise ConfigError("topics_source.inline_topics must be a list when type is inline.")

    timeout_raw = data.get("ollama", {}).get("timeouts", {})
    timeouts = Timeouts(
        connect_seconds=int(timeout_raw.get("connect_seconds", 10)),
        read_seconds=int(timeout_raw.get("read_seconds", 600)),
    )
    if timeouts.connect_seconds <= 0 or timeouts.read_seconds <= 0:
        raise ConfigError("Ollama timeout values must be positive integers.")

    ollama_raw = data.get("ollama", {})
    ollama = OllamaConfig(
        base_url=str(ollama_raw.get("base_url", "http://localhost:11434")).rstrip("/"),
        model=str(ollama_raw.get("model", "llama3.1:8b")),
        max_retries=int(ollama_raw.get("max_retries", 2)),
        timeouts=timeouts,
    )
    if ollama.max_retries < 0:
        raise ConfigError("ollama.max_retries must be >= 0.")

    streams = _validate_streams(data.get("streams", []))
    if not any(s.enabled for s in streams):
        raise ConfigError("At least one stream must be enabled in config.")

    batch_size = int(data.get("batch_size", 30))
    if batch_size <= 0:
        raise ConfigError("batch_size must be > 0.")

    return PipelineConfig(
        pipeline_version=str(data.get("pipeline_version", "1.0")),
        model_policy=model_policy,
        niche=str(data.get("niche", "personal finance")),
        target_audience=str(data.get("target_audience", "working adults 25-45")),
        tone=str(data.get("tone", "clear, practical, motivational")),
        language=str(data.get("language", "English")),
        output_root=str(data.get("output_root", "runs")),
        prompts_root=str(data.get("prompts_root", "prompts")),
        batch_size=batch_size,
        checkpointing=bool(data.get("checkpointing", True)),
        topics_source=topics_source,
        ollama=ollama,
        streams=streams,
    )


def load_config(path: str) -> PipelineConfig:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigError(f"Config file does not exist: {cfg_path}")
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    merged = _deep_merge(DEFAULT_CONFIG, raw)
    base_dir = cfg_path.resolve().parent
    output_root = Path(str(merged.get("output_root", "runs")))
    if not output_root.is_absolute():
        merged["output_root"] = str((base_dir / output_root).resolve())
    prompts_root = Path(str(merged.get("prompts_root", "prompts")))
    if not prompts_root.is_absolute():
        merged["prompts_root"] = str((base_dir / prompts_root).resolve())
    topics_source = merged.get("topics_source", {})
    topics_path = Path(str(topics_source.get("path", "")))
    if topics_path and not topics_path.is_absolute():
        topics_source["path"] = str((base_dir / topics_path).resolve())
        merged["topics_source"] = topics_source
    return _validate_and_build(merged)


def write_example_config(path: str) -> None:
    out_path = Path(path)
    out_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

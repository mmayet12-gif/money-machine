from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from .config import ConfigError, load_config, write_example_config
from .ollama import OllamaError
from .pipeline import MoneyMachinePipeline


def _parse_streams(raw: str) -> List[str]:
    if not raw:
        return []
    return [x.strip().upper() for x in raw.split(",") if x.strip()]


def _print_status(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="money-machine", description="Local Money Machine content pipeline.")
    parser.add_argument("--config", default="pipeline_config.json", help="Path to pipeline config JSON.")

    sub = parser.add_subparsers(dest="command", required=True)

    plan_cmd = sub.add_parser("plan", help="Validate config and print selected streams.")
    plan_cmd.add_argument("--config", default="pipeline_config.json", help="Path to pipeline config JSON.")

    run_cmd = sub.add_parser("run", help="Execute pipeline.")
    run_cmd.add_argument("--config", default="pipeline_config.json", help="Path to pipeline config JSON.")
    run_cmd.add_argument("--streams", default="", help="Comma-separated stream IDs (e.g., S1,S3,S5).")
    run_cmd.add_argument("--run-id", default="", help="Optional run ID. Defaults to UTC timestamp.")

    resume_cmd = sub.add_parser("resume", help="Resume a previous run ID.")
    resume_cmd.add_argument("--config", default="pipeline_config.json", help="Path to pipeline config JSON.")
    resume_cmd.add_argument("--run-id", required=True, help="Run ID to resume.")
    resume_cmd.add_argument("--streams", default="", help="Optional stream filter.")

    retry_cmd = sub.add_parser("retry", help="Retry failed units only.")
    retry_cmd.add_argument("--config", default="pipeline_config.json", help="Path to pipeline config JSON.")
    retry_cmd.add_argument("--run-id", required=True, help="Run ID to retry.")
    retry_cmd.add_argument("--streams", default="", help="Optional stream filter.")

    status_cmd = sub.add_parser("status", help="Show status for a run.")
    status_cmd.add_argument("--config", default="pipeline_config.json", help="Path to pipeline config JSON.")
    status_cmd.add_argument("--run-id", required=True, help="Run ID to inspect.")

    init_cmd = sub.add_parser("init-config", help="Write example config JSON.")
    init_cmd.add_argument("--output", default="pipeline_config.example.json", help="Output path.")
    doctor_cmd = sub.add_parser("doctor", help="Check required local files and Ollama availability.")
    doctor_cmd.add_argument("--config", default="pipeline_config.json", help="Path to pipeline config JSON.")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-config":
        write_example_config(args.output)
        print(f"Wrote example config to {Path(args.output).resolve()}")
        return 0

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    pipeline = MoneyMachinePipeline(cfg)

    try:
        if args.command == "plan":
            selected = [s.stream_id for s in cfg.streams if s.enabled]
            _print_status(
                {
                    "pipeline_version": cfg.pipeline_version,
                    "model_policy": cfg.model_policy,
                    "niche": cfg.niche,
                    "output_root": str(Path(cfg.output_root).resolve()),
                    "enabled_streams": selected,
                    "batch_size": cfg.batch_size,
                }
            )
            return 0
        if args.command == "doctor":
            checks = {
                "config_loaded": True,
                "output_root_exists": Path(cfg.output_root).exists(),
                "prompts_root_exists": Path(cfg.prompts_root).exists(),
                "topics_path_exists": bool(cfg.topics_source.path and Path(cfg.topics_source.path).exists()),
                "ollama_healthy": pipeline.client.health_check(),
            }
            _print_status(checks)
            return 0

        if args.command == "run":
            status = pipeline.run(
                run_id=args.run_id or None,
                stream_filter=_parse_streams(args.streams),
            )
            _print_status(status.__dict__)
            return 0

        if args.command == "resume":
            status = pipeline.run(
                run_id=args.run_id,
                stream_filter=_parse_streams(args.streams),
            )
            _print_status(status.__dict__)
            return 0

        if args.command == "retry":
            status = pipeline.run(
                run_id=args.run_id,
                stream_filter=_parse_streams(args.streams),
                retry_failed_only=True,
            )
            _print_status(status.__dict__)
            return 0

        if args.command == "status":
            status = pipeline.status(args.run_id)
            _print_status(status.__dict__)
            return 0
    except (OllamaError, ValueError) as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 3

    return 1

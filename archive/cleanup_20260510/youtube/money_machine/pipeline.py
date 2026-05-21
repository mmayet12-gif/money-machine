from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .config import PipelineConfig, StreamConfig
from .filesystem import ensure_dir, utc_stamp
from .ollama import OllamaClient, OllamaError
from .state import StreamState, load_run_summary, save_failures, save_run_summary
from .streams import STREAM_BUILDERS
from .text_utils import normalize_text
from .topic_loader import load_topics
from .types import GenerationResult, GenerationUnit


@dataclass
class PipelineStatus:
    run_id: str
    status: str
    streams: Dict[str, Dict[str, object]]
    failures: List[Dict[str, str]]


class MoneyMachinePipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.client = OllamaClient(config.ollama)
        self.root = Path(config.output_root)
        ensure_dir(self.root)

    def _resolve_streams(self, stream_filter: Optional[Sequence[str]]) -> List[StreamConfig]:
        enabled = [s for s in self.config.streams if s.enabled]
        if not stream_filter:
            return enabled
        requested = {x.strip().upper() for x in stream_filter if x.strip()}
        return [s for s in enabled if s.stream_id in requested]

    def _stream_dirs(self, run_dir: Path, stream: StreamConfig) -> Dict[str, Path]:
        stream_dir = ensure_dir(run_dir / stream.stream_id)
        return {
            "stream_dir": stream_dir,
            "outputs_dir": ensure_dir(stream_dir / "outputs"),
            "progress_path": stream_dir / "progress.json",
            "manifest_path": stream_dir / "manifest.jsonl",
        }

    def _write_artifacts(
        self,
        outputs_dir: Path,
        stream: StreamConfig,
        unit: GenerationUnit,
        content: str,
    ) -> List[str]:
        artifact_paths: List[str] = []
        for fmt in stream.output_formats:
            out_path = outputs_dir / f"{unit.unit_id}.{fmt}"
            if fmt == "html":
                body = (
                    "<!doctype html>\n"
                    "<html><head><meta charset=\"utf-8\"><title>"
                    f"{unit.title}"
                    "</title></head><body><pre>\n"
                    f"{content}"
                    "\n</pre></body></html>\n"
                )
                out_path.write_text(body, encoding="utf-8")
            else:
                out_path.write_text(content, encoding="utf-8")
            artifact_paths.append(str(out_path.resolve()))
        return artifact_paths

    def _run_stream(
        self,
        run_id: str,
        run_dir: Path,
        stream: StreamConfig,
        retry_failed_only: bool = False,
    ) -> Dict[str, object]:
        if stream.stream_id not in STREAM_BUILDERS:
            raise ValueError(f"No builder registered for stream {stream.stream_id}.")

        topics = load_topics(self.config)
        units = STREAM_BUILDERS[stream.stream_id](stream, self.config, topics)
        paths = self._stream_dirs(run_dir, stream)
        state = StreamState(paths["progress_path"], paths["manifest_path"])
        progress = state.load_progress()
        completed = set(progress.get("completed", []))
        failed = set(progress.get("failed", []))
        stream_failures: List[Dict[str, str]] = []

        for unit in units:
            if unit.unit_id in completed:
                continue
            if retry_failed_only and unit.unit_id not in failed:
                continue

            try:
                raw = self.client.generate(unit.prompt)
                normalized = normalize_text(raw, ascii_only=True)
                artifacts = self._write_artifacts(paths["outputs_dir"], stream, unit, normalized)
                state.mark_completed(unit.unit_id, total_units=len(units))
                state.append_manifest(
                    {
                        "run_id": run_id,
                        "stream_id": stream.stream_id,
                        "unit_id": unit.unit_id,
                        "status": "completed",
                        "timestamp_utc": datetime.utcnow().isoformat(),
                        "artifacts": artifacts,
                    }
                )
            except Exception as exc:
                err = str(exc)
                stream_failures.append({"stream_id": stream.stream_id, "unit_id": unit.unit_id, "error": err})
                state.mark_failed(unit.unit_id, total_units=len(units))
                state.append_manifest(
                    {
                        "run_id": run_id,
                        "stream_id": stream.stream_id,
                        "unit_id": unit.unit_id,
                        "status": "failed",
                        "timestamp_utc": datetime.utcnow().isoformat(),
                        "error": err,
                    }
                )

        latest = state.load_progress()
        done_count = len(latest.get("completed", []))
        failed_count = len(latest.get("failed", []))
        return {
            "stream_id": stream.stream_id,
            "name": stream.name,
            "total": len(units),
            "completed": done_count,
            "failed": failed_count,
            "status": "completed" if failed_count == 0 and done_count == len(units) else "partial",
            "failures": stream_failures,
        }

    def run(
        self,
        run_id: Optional[str] = None,
        stream_filter: Optional[Iterable[str]] = None,
        retry_failed_only: bool = False,
    ) -> PipelineStatus:
        if not self.client.health_check():
            raise OllamaError(
                "Ollama health check failed. Start local Ollama server and ensure the model is available."
            )

        selected_streams = self._resolve_streams(list(stream_filter or []))
        if not selected_streams:
            raise ValueError("No streams selected for execution.")

        resolved_run_id = run_id or utc_stamp()
        run_dir = ensure_dir(self.root / resolved_run_id)
        summary_path = run_dir / "run_summary.json"
        failures_path = run_dir / "failures.json"

        summary = load_run_summary(summary_path)
        if not summary.get("run_id"):
            summary["run_id"] = resolved_run_id
            summary["started_at_utc"] = datetime.utcnow().isoformat()
        summary["status"] = "running"
        save_run_summary(summary_path, summary)

        all_failures: List[Dict[str, str]] = []
        for stream in selected_streams:
            result = self._run_stream(
                run_id=resolved_run_id,
                run_dir=run_dir,
                stream=stream,
                retry_failed_only=retry_failed_only,
            )
            summary.setdefault("streams", {})[stream.stream_id] = {
                "name": result["name"],
                "total": result["total"],
                "completed": result["completed"],
                "failed": result["failed"],
                "status": result["status"],
            }
            all_failures.extend(result["failures"])
            save_run_summary(summary_path, summary)

        summary["status"] = "completed" if not all_failures else "partial"
        summary["finished_at_utc"] = datetime.utcnow().isoformat()
        save_run_summary(summary_path, summary)
        save_failures(failures_path, all_failures)

        return PipelineStatus(
            run_id=resolved_run_id,
            status=summary["status"],
            streams=summary.get("streams", {}),
            failures=all_failures,
        )

    def status(self, run_id: str) -> PipelineStatus:
        run_dir = self.root / run_id
        summary = load_run_summary(run_dir / "run_summary.json")
        failures_file = run_dir / "failures.json"
        failures = []
        if failures_file.exists():
            import json

            failures = json.loads(failures_file.read_text(encoding="utf-8")).get("failures", [])
        return PipelineStatus(
            run_id=run_id,
            status=summary.get("status", "unknown"),
            streams=summary.get("streams", {}),
            failures=failures,
        )

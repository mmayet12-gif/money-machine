from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .filesystem import append_jsonl, read_json, write_json


@dataclass
class StreamState:
    progress_path: Path
    manifest_path: Path

    def load_progress(self) -> Dict[str, object]:
        return read_json(
            self.progress_path,
            {"completed": [], "failed": [], "updated_at": "", "total_units": 0},
        )

    def save_progress(self, progress: Dict[str, object]) -> None:
        write_json(self.progress_path, progress)

    def mark_completed(self, unit_id: str, total_units: int) -> None:
        progress = self.load_progress()
        completed = set(progress.get("completed", []))
        failed = set(progress.get("failed", []))
        completed.add(unit_id)
        failed.discard(unit_id)
        progress["completed"] = sorted(completed)
        progress["failed"] = sorted(failed)
        progress["total_units"] = total_units
        self.save_progress(progress)

    def mark_failed(self, unit_id: str, total_units: int) -> None:
        progress = self.load_progress()
        failed = set(progress.get("failed", []))
        completed = set(progress.get("completed", []))
        if unit_id not in completed:
            failed.add(unit_id)
        progress["failed"] = sorted(failed)
        progress["total_units"] = total_units
        self.save_progress(progress)

    def append_manifest(self, item: Dict[str, object]) -> None:
        append_jsonl(self.manifest_path, item)


def load_run_summary(path: Path) -> Dict[str, object]:
    return read_json(
        path,
        {
            "run_id": "",
            "status": "running",
            "streams": {},
            "started_at_utc": "",
            "finished_at_utc": "",
        },
    )


def save_run_summary(path: Path, data: Dict[str, object]) -> None:
    write_json(path, data)


def save_failures(path: Path, failures: List[Dict[str, str]]) -> None:
    write_json(path, {"failures": failures, "count": len(failures)})

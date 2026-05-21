#!/usr/bin/env python3
"""
Upload Queue Manager — schedule videos for automated upload.

Usage:
    python queue_manager.py add <video> [--at "2026-05-10 09:00"] [--kind long_form|short]
    python queue_manager.py list [--pending|--uploaded|--failed|--all]
    python queue_manager.py remove <id>
    python queue_manager.py reschedule <id> --at "2026-05-10 09:00"
    python queue_manager.py auto-fill <video_dir>
    python queue_manager.py next-slot --kind long_form|short
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"C:\money-machine")
CONFIG_DIR = ROOT / "config"
METADATA_DIR = ROOT / "output" / "metadata"
QUEUE_FILE = CONFIG_DIR / "upload_queue.json"

LONG_FORM_DAYS = {0, 2, 4}  # Monday, Wednesday, Friday
LONG_FORM_WINDOW = (9, 18)
LONG_FORM_DEFAULT_HOUR = 9
SHORT_WINDOW = (9, 21)
SHORT_DEFAULT_HOUR = 12
MAX_SHORTS_PER_DAY = 1
MIN_LONG_FORM_GAP_HOURS = 24


def load_queue() -> dict:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"queue": []}


def save_queue(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def next_available_slot(kind: str, queue: list[dict]) -> datetime:
    now = datetime.now()
    active = [
        q for q in queue
        if q["status"] in ("pending", "uploading") and q["kind"] == kind
    ]
    scheduled_times = []
    for q in active:
        try:
            scheduled_times.append(datetime.fromisoformat(q["scheduled_for"]))
        except (ValueError, KeyError):
            pass

    if kind == "long_form":
        candidate = now.replace(hour=LONG_FORM_DEFAULT_HOUR, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)

        for _ in range(365):
            if candidate.weekday() not in LONG_FORM_DAYS:
                candidate += timedelta(days=1)
                continue

            too_close = False
            for t in scheduled_times:
                if abs((candidate - t).total_seconds()) < MIN_LONG_FORM_GAP_HOURS * 3600:
                    too_close = True
                    break
            if too_close:
                candidate += timedelta(days=1)
                continue

            return candidate
    else:
        candidate = now.replace(hour=SHORT_DEFAULT_HOUR, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)

        for _ in range(365):
            day_start = candidate.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            shorts_that_day = sum(
                1 for t in scheduled_times
                if day_start <= t < day_end
            )
            if shorts_that_day >= MAX_SHORTS_PER_DAY:
                candidate += timedelta(days=1)
                continue

            return candidate

    raise RuntimeError("Could not find an available slot within 365 days")


def find_metadata_path(video_path: Path) -> Path | None:
    stem = video_path.stem
    exact = METADATA_DIR / f"{stem}.json"
    if exact.exists():
        return exact
    for c in sorted(METADATA_DIR.glob("*.json")):
        if stem.startswith(c.stem[:5]):
            return c
    return None


def infer_kind(video_path: Path) -> str:
    if "short" in video_path.stem.lower() or "short" in str(video_path.parent).lower():
        return "short"
    return "long_form"


def make_entry(
    video_path: Path,
    scheduled_for: datetime,
    kind: str,
    metadata_path: Path | None,
) -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "video_path": str(video_path),
        "metadata_path": str(metadata_path) if metadata_path else None,
        "scheduled_for": scheduled_for.isoformat(),
        "kind": kind,
        "status": "pending",
        "added_at": datetime.now().isoformat(),
        "uploaded_at": None,
        "video_id": None,
        "studio_url": None,
        "error": None,
        "retry_count": 0,
    }


def already_queued(queue: list[dict], video_path: Path) -> bool:
    vp = str(video_path)
    return any(
        q["video_path"] == vp and q["status"] in ("pending", "uploading", "uploaded")
        for q in queue
    )


def cmd_add(args) -> int:
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"ERROR: File not found: {video_path}")
        return 1

    file_size_gb = video_path.stat().st_size / (1024 ** 3)
    if file_size_gb > 256:
        print(f"ERROR: File is {file_size_gb:.1f} GB — exceeds YouTube's 256 GB limit")
        return 1

    kind = args.kind or infer_kind(video_path)
    meta_path = find_metadata_path(video_path)
    if meta_path is None:
        print(f"WARNING: No metadata JSON found for {video_path.name}")

    data = load_queue()

    if already_queued(data["queue"], video_path):
        print(f"Already in queue: {video_path.name}")
        return 0

    if args.at:
        scheduled = datetime.fromisoformat(args.at.replace(" ", "T"))
    else:
        scheduled = next_available_slot(kind, data["queue"])

    entry = make_entry(video_path, scheduled, kind, meta_path)
    data["queue"].append(entry)
    save_queue(data)

    print(f"Added to queue:")
    print(f"  ID:        {entry['id']}")
    print(f"  Video:     {video_path.name}")
    print(f"  Kind:      {kind}")
    print(f"  Scheduled: {scheduled.strftime('%Y-%m-%d %H:%M')}")
    return 0


def cmd_list(args) -> int:
    data = load_queue()
    items = data["queue"]

    if args.pending:
        items = [q for q in items if q["status"] == "pending"]
    elif args.uploaded:
        items = [q for q in items if q["status"] == "uploaded"]
    elif args.failed:
        items = [q for q in items if q["status"] == "failed"]
    elif not args.all:
        items = [q for q in items if q["status"] in ("pending", "uploading")]

    if not items:
        print("Queue is empty.")
        return 0

    fmt = "{:<10s} {:<18s} {:<12s} {:<42s} {:<10s}"
    print(fmt.format("ID", "SCHEDULED", "KIND", "TITLE", "STATUS"))
    print("-" * 94)
    for q in sorted(items, key=lambda x: x.get("scheduled_for", "")):
        title = Path(q["video_path"]).stem[:40] if q["video_path"] else "?"
        sched = q.get("scheduled_for", "")[:16].replace("T", " ")
        print(fmt.format(
            q["id"][:8],
            sched,
            q.get("kind", "?"),
            title,
            q["status"],
        ))

    counts = {}
    for q in data["queue"]:
        counts[q["status"]] = counts.get(q["status"], 0) + 1
    parts = [f"{v} {k}" for k, v in sorted(counts.items())]
    print(f"\nTotal: {len(data['queue'])} ({', '.join(parts)})")
    return 0


def cmd_remove(args) -> int:
    data = load_queue()
    for q in data["queue"]:
        if q["id"].startswith(args.id):
            q["status"] = "cancelled"
            save_queue(data)
            print(f"Cancelled: {q['id']} — {Path(q['video_path']).stem}")
            return 0
    print(f"ERROR: No queue entry matching ID '{args.id}'")
    return 1


def cmd_reschedule(args) -> int:
    if not args.at:
        print("ERROR: --at is required. Example: --at \"2026-05-10 09:00\"")
        return 1

    data = load_queue()
    for q in data["queue"]:
        if q["id"].startswith(args.id):
            if q["status"] != "pending":
                print(f"ERROR: Can only reschedule pending items (current: {q['status']})")
                return 1
            new_time = datetime.fromisoformat(args.at.replace(" ", "T"))
            q["scheduled_for"] = new_time.isoformat()
            save_queue(data)
            print(f"Rescheduled {q['id']} to {new_time.strftime('%Y-%m-%d %H:%M')}")
            return 0
    print(f"ERROR: No queue entry matching ID '{args.id}'")
    return 1


def cmd_auto_fill(args) -> int:
    video_dir = Path(args.video_dir).resolve()
    if not video_dir.exists():
        print(f"ERROR: Directory not found: {video_dir}")
        return 1

    mp4s = sorted(video_dir.glob("*.mp4"))
    if not mp4s:
        print(f"No .mp4 files found in {video_dir}")
        return 0

    data = load_queue()
    new_entries = []

    for mp4 in mp4s:
        if already_queued(data["queue"], mp4):
            continue
        kind = infer_kind(mp4)
        meta_path = find_metadata_path(mp4)
        all_items = data["queue"] + new_entries
        slot = next_available_slot(kind, all_items)
        entry = make_entry(mp4, slot, kind, meta_path)
        new_entries.append(entry)

    if not new_entries:
        print("All videos are already queued.")
        return 0

    print(f"\nProposed schedule ({len(new_entries)} videos):\n")
    fmt = "{:<10s} {:<18s} {:<12s} {:<45s}"
    print(fmt.format("ID", "SCHEDULED", "KIND", "VIDEO"))
    print("-" * 87)
    for e in new_entries:
        sched = e["scheduled_for"][:16].replace("T", " ")
        print(fmt.format(e["id"][:8], sched, e["kind"], Path(e["video_path"]).name[:43]))

    answer = input(f"\nAdd all {len(new_entries)} to the queue? [y/N] ").strip().lower()
    if answer != "y":
        print("Cancelled. Nothing was added.")
        return 0

    data["queue"].extend(new_entries)
    save_queue(data)
    print(f"\nAdded {len(new_entries)} videos to the queue.")
    return 0


def cmd_next_slot(args) -> int:
    if not args.kind:
        print("ERROR: --kind is required (long_form or short)")
        return 1
    data = load_queue()
    slot = next_available_slot(args.kind, data["queue"])
    day_name = slot.strftime("%A")
    print(f"Next available {args.kind} slot: {slot.strftime('%Y-%m-%d %H:%M')} ({day_name})")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Upload queue manager — schedule videos for YouTube upload",
    )
    sub = p.add_subparsers(dest="command")

    # add
    add_p = sub.add_parser("add", help="Add a video to the upload queue")
    add_p.add_argument("video", help="Path to the .mp4 file")
    add_p.add_argument("--at", help="Schedule time: \"2026-05-10 09:00\"")
    add_p.add_argument("--kind", choices=["long_form", "short"], help="Video kind")

    # list
    list_p = sub.add_parser("list", help="List queued videos")
    list_p.add_argument("--pending", action="store_true")
    list_p.add_argument("--uploaded", action="store_true")
    list_p.add_argument("--failed", action="store_true")
    list_p.add_argument("--all", action="store_true")

    # remove
    rm_p = sub.add_parser("remove", help="Cancel a queued video")
    rm_p.add_argument("id", help="Queue entry ID (or prefix)")

    # reschedule
    rs_p = sub.add_parser("reschedule", help="Change the schedule for a pending video")
    rs_p.add_argument("id", help="Queue entry ID (or prefix)")
    rs_p.add_argument("--at", help="New schedule time", required=True)

    # auto-fill
    af_p = sub.add_parser("auto-fill", help="Auto-schedule all unqueued videos in a directory")
    af_p.add_argument("video_dir", help="Directory containing .mp4 files")

    # next-slot
    ns_p = sub.add_parser("next-slot", help="Show the next available upload slot")
    ns_p.add_argument("--kind", choices=["long_form", "short"], required=True)

    args = p.parse_args()

    if args.command == "add":
        return cmd_add(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "remove":
        return cmd_remove(args)
    if args.command == "reschedule":
        return cmd_reschedule(args)
    if args.command == "auto-fill":
        return cmd_auto_fill(args)
    if args.command == "next-slot":
        return cmd_next_slot(args)

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

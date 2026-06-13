"""Helpers for reading persisted snapshot artifacts."""

from __future__ import annotations

from typing import Any

from src.adaptive.snapshotter import SnapshotManager


def list_snapshot_details() -> list[dict[str, Any]]:
    """Return snapshot metadata ordered chronologically."""

    manager = SnapshotManager()
    if hasattr(manager, "list_snapshot_details"):
        return manager.list_snapshot_details()
    return [
        {
            "snapshot_id": snapshot_id,
            "descriptor": snapshot_id.split("_", 1)[-1],
            "created_at": None,
            "resolved_matches": [],
            "model_metadata": {},
        }
        for snapshot_id in manager.list_snapshots()
    ]


def latest_snapshot_id() -> str | None:
    """Return the most recent snapshot id, if any."""

    snapshots = SnapshotManager().list_snapshots()
    if not snapshots:
        return None
    return snapshots[-1]


def resolve_snapshot_id(snapshot_id: str | None = None) -> str | None:
    """Use the requested snapshot id or fall back to the latest one."""

    return snapshot_id or latest_snapshot_id()


def load_snapshot_file(file_name: str, snapshot_id: str | None = None, default: Any | None = None) -> Any:
    """Read one file from the selected snapshot."""

    resolved_snapshot_id = resolve_snapshot_id(snapshot_id)
    if resolved_snapshot_id is None:
        return default
    return SnapshotManager().read_snapshot(resolved_snapshot_id, file_name) or default

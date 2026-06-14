"""Helpers for reading persisted snapshot artifacts."""

from __future__ import annotations

import copy
from functools import lru_cache
from typing import Any

from pathlib import Path

from src.adaptive.snapshotter import SnapshotManager
from src.utils.helpers import load_json


def _snapshot_path(snapshot_id: str, file_name: str) -> Path:
    return SnapshotManager().snapshot_dir(snapshot_id) / file_name


@lru_cache(maxsize=256)
def _load_snapshot_json_cached(path_str: str, mtime_ns: int) -> Any:
    return load_json(Path(path_str))


@lru_cache(maxsize=16)
def _list_snapshot_details_cached(signature: tuple[tuple[str, int], ...]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for snapshot_id, _ in signature:
        payload = _load_snapshot_json_cached(
            str(_snapshot_path(snapshot_id, "snapshot.json")),
            _snapshot_path(snapshot_id, "snapshot.json").stat().st_mtime_ns,
        ) or {}
        details.append(
            {
                "snapshot_id": snapshot_id,
                "descriptor": payload.get("descriptor", snapshot_id.split("_", 1)[-1]),
                "created_at": payload.get("created_at"),
                "resolved_matches": payload.get("resolved_matches", []),
                "model_metadata": payload.get("model_metadata", {}),
            }
        )
    return details


def list_snapshot_details() -> list[dict[str, Any]]:
    """Return snapshot metadata ordered chronologically."""

    manager = SnapshotManager()
    signature = tuple(
        (
            snapshot_id,
            (_snapshot_path(snapshot_id, "snapshot.json").stat().st_mtime_ns
             if _snapshot_path(snapshot_id, "snapshot.json").exists()
             else -1),
        )
        for snapshot_id in manager.list_snapshots()
    )
    return copy.deepcopy(_list_snapshot_details_cached(signature))


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
    path = _snapshot_path(resolved_snapshot_id, file_name)
    if not path.exists():
        return default
    payload = _load_snapshot_json_cached(str(path), path.stat().st_mtime_ns)
    return copy.deepcopy(payload) if payload is not None else default

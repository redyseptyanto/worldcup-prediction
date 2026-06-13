"""Snapshot timeline helpers."""

from __future__ import annotations

from src.visualization.snapshot_store import list_snapshot_details


def list_snapshot_timeline() -> list[dict[str, object]]:
    """List available snapshots in chronological order with metadata."""

    return list_snapshot_details()

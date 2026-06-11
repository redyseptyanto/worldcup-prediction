"""Snapshot timeline helpers."""

from __future__ import annotations

from src.adaptive.snapshotter import SnapshotManager


def list_snapshot_timeline() -> list[str]:
    """List available snapshots in chronological order."""

    return SnapshotManager().list_snapshots()

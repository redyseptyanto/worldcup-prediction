"""Standings rendering helpers."""

from __future__ import annotations

from src.visualization.snapshot_store import load_snapshot_file


def load_latest_standings(snapshot_id: str | None = None) -> dict[str, object]:
    """Load standings from the selected snapshot."""

    return load_snapshot_file("standings.json", snapshot_id=snapshot_id, default={})

"""Bracket rendering helpers."""

from __future__ import annotations

from src.visualization.snapshot_store import load_snapshot_file


def load_latest_bracket(snapshot_id: str | None = None) -> dict[str, object]:
    """Load bracket data from the selected snapshot."""

    return load_snapshot_file("bracket_data.json", snapshot_id=snapshot_id, default={})

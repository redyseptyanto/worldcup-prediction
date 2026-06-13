"""Probability table helpers."""

from __future__ import annotations

from src.visualization.snapshot_store import load_snapshot_file


def probability_table(snapshot_id: str | None = None) -> list[dict[str, object]]:
    """Return the selected snapshot's prediction table."""

    return load_snapshot_file("predictions.json", snapshot_id=snapshot_id, default=[])

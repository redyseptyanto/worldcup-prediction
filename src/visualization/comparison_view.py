"""Snapshot comparison helpers for the dashboard."""

from __future__ import annotations

from src.adaptive.engine import AdaptiveEngine


def compare_snapshots(from_snapshot: str, to_snapshot: str) -> dict[str, object]:
    """Compare two stored snapshots."""

    engine = AdaptiveEngine()
    return engine.compare_snapshots(from_snapshot, to_snapshot)

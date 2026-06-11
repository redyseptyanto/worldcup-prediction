"""Standings rendering helpers."""

from __future__ import annotations

from src.config import SETTINGS
from src.utils.helpers import load_json


def load_latest_standings() -> dict[str, object]:
    """Load standings from the latest snapshot."""

    snapshots = sorted(path.name for path in SETTINGS.snapshots_dir.iterdir() if path.is_dir())
    if not snapshots:
        return {}
    latest = snapshots[-1]
    return load_json(SETTINGS.snapshots_dir / latest / "standings.json", default={})

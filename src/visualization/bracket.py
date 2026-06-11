"""Bracket rendering helpers."""

from __future__ import annotations

from src.config import SETTINGS
from src.utils.helpers import load_json


def load_latest_bracket() -> dict[str, object]:
    """Load the latest bracket snapshot if one exists."""

    snapshots = sorted(path.name for path in SETTINGS.snapshots_dir.iterdir() if path.is_dir())
    if not snapshots:
        return {}
    latest = snapshots[-1]
    return load_json(SETTINGS.snapshots_dir / latest / "bracket_data.json", default={})

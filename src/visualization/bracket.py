"""Bracket rendering helpers."""

from __future__ import annotations

from src.config import SETTINGS
from src.simulation.knockout_stage import align_projected_match_score
from src.utils.helpers import load_json, save_json
from src.visualization.snapshot_store import load_snapshot_file


def _repair_bracket_payload(bracket_data: dict[str, object]) -> dict[str, object]:
    if not isinstance(bracket_data, dict):
        return {}

    bracket = bracket_data.get("bracket", {})
    if not isinstance(bracket, dict):
        return bracket_data

    repaired_bracket = dict(bracket)
    for stage_name in ("round_of_32", "round_of_16", "quarter_finals", "semi_finals"):
        stage_matches = repaired_bracket.get(stage_name, [])
        if isinstance(stage_matches, list):
            repaired_bracket[stage_name] = [align_projected_match_score(match) for match in stage_matches]
    for stage_name in ("third_place", "final"):
        stage_match = repaired_bracket.get(stage_name)
        if isinstance(stage_match, dict):
            repaired_bracket[stage_name] = align_projected_match_score(stage_match)
    return {**bracket_data, "bracket": repaired_bracket}


def repair_snapshot_bracket(snapshot_id: str) -> bool:
    """Persist repaired knockout scorelines for one stored snapshot."""

    path = SETTINGS.snapshots_dir / snapshot_id / "bracket_data.json"
    if not path.exists():
        return False
    original = load_json(path, default={})
    repaired = _repair_bracket_payload(original)
    if repaired != original:
        save_json(path, repaired)
        return True
    return False


def load_latest_bracket(snapshot_id: str | None = None) -> dict[str, object]:
    """Load bracket data from the selected snapshot."""

    bracket_data = load_snapshot_file("bracket_data.json", snapshot_id=snapshot_id, default={})
    return _repair_bracket_payload(bracket_data)

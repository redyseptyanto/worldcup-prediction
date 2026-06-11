"""Determine downstream matches affected by an ingest."""

from __future__ import annotations

from src.adaptive.state_machine import MatchStateMachine


class CascadeAnalyzer:
    """Simple cascade analysis for the demo tournament."""

    def __init__(self, state_machine: MatchStateMachine) -> None:
        self.state_machine = state_machine

    def get_affected_matches(self, resolved_match_id: str) -> list[str]:
        match = self.state_machine.get(resolved_match_id)
        if match is None:
            return []
        affected = [
            item["match_id"]
            for item in self.state_machine.list_matches()
            if item["match_id"] != resolved_match_id
            and item["group"] == match["group"]
            and item["state"] != "RESOLVED"
        ]
        affected.extend([f"R32-{index}" for index in range(1, 17)])
        affected.extend([f"R16-{index}" for index in range(1, 9)])
        affected.extend([f"QF-{index}" for index in range(1, 5)])
        affected.extend(["SF-1", "SF-2", "THIRD-1", "FINAL-1"])
        return sorted(set(affected))

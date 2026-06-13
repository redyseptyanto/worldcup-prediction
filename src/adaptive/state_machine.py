"""File-backed match state transitions."""

from __future__ import annotations

from typing import Any

from src.config import MATCH_STATE_FILE
from src.data.loaders import get_state_store, initialize_state_store
from src.simulation.knockout_stage import flatten_bracket_matches
from src.utils.constants import (
    MATCH_STATE_PENDING,
    MATCH_STATE_POSTPONED,
    MATCH_STATE_RESOLVED,
)
from src.utils.helpers import save_json


class MatchStateMachine:
    """Manage forward-only match state transitions."""

    def __init__(self) -> None:
        self._state = get_state_store()

    def refresh(self) -> None:
        self._state = get_state_store()

    def list_matches(self) -> list[dict[str, Any]]:
        return list(self._state.values())

    def get(self, match_id: str) -> dict[str, Any] | None:
        return self._state.get(match_id)

    def set_resolved(self, match_id: str, home_goals: int, away_goals: int, winner: str | None = None) -> dict[str, Any]:
        if match_id not in self._state:
            raise KeyError(f"Unknown match id: {match_id}")
        current = self._state[match_id]
        if current["state"] == MATCH_STATE_RESOLVED:
            raise ValueError(f"Match {match_id} is already resolved.")
        current["state"] = MATCH_STATE_RESOLVED
        current["home_goals"] = int(home_goals)
        current["away_goals"] = int(away_goals)
        current["winner"] = winner
        save_json(MATCH_STATE_FILE, self._state)
        return current

    def set_postponed(self, match_id: str) -> dict[str, Any]:
        current = self._state[match_id]
        current["state"] = MATCH_STATE_POSTPONED
        save_json(MATCH_STATE_FILE, self._state)
        return current

    def reset(self, snapshot_state: dict[str, Any] | None = None) -> None:
        if snapshot_state is None:
            initialize_state_store()
        else:
            save_json(MATCH_STATE_FILE, snapshot_state)
        self.refresh()

    def resolved_results(self) -> dict[str, dict[str, Any]]:
        return {
            match_id: {
                "home_goals": state["home_goals"],
                "away_goals": state["away_goals"],
                "winner": state.get("winner"),
            }
            for match_id, state in self._state.items()
            if state["state"] == MATCH_STATE_RESOLVED
        }

    def sync_knockout_matches(self, simulation_output: dict[str, Any]) -> None:
        """Update knockout placeholders with the latest participant assignments."""

        bracket = simulation_output.get("knockout", {}).get("bracket", {})
        changed = False
        for match in flatten_bracket_matches(bracket):
            current = self._state.get(match["match_id"])
            if current is None:
                continue
            if current["state"] == MATCH_STATE_RESOLVED:
                continue
            home_team = match.get("home_team", "TBD")
            away_team = match.get("away_team", "TBD")
            if current.get("home_team") != home_team:
                current["home_team"] = home_team
                changed = True
            if current.get("away_team") != away_team:
                current["away_team"] = away_team
                changed = True
            if current.get("stage") != match.get("round", current.get("stage")):
                current["stage"] = match.get("round", current["stage"])
                changed = True
            current["round"] = match.get("round", current.get("round", ""))
            current["annex_c"] = match.get("annex_c", current.get("annex_c", ""))
        if changed:
            save_json(MATCH_STATE_FILE, self._state)

    @property
    def pending_state(self) -> str:
        return MATCH_STATE_PENDING

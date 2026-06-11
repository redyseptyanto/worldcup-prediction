"""Result ingestion validation."""

from __future__ import annotations

from dataclasses import dataclass

from src.adaptive.state_machine import MatchStateMachine


@dataclass(frozen=True)
class IngestResult:
    """Structured ingest response."""

    match_id: str
    home_goals: int
    away_goals: int


class ResultIngester:
    """Validate and apply real match results."""

    def __init__(self, state_machine: MatchStateMachine) -> None:
        self.state_machine = state_machine

    def ingest(self, match_id: str, home_goals: int, away_goals: int) -> IngestResult:
        match = self.state_machine.get(match_id)
        if match is None:
            raise KeyError(f"Unknown match id: {match_id}")
        if match["state"] == "RESOLVED":
            raise ValueError(f"Match {match_id} has already been ingested.")
        if not (0 <= home_goals <= 15 and 0 <= away_goals <= 15):
            raise ValueError("Goals must be between 0 and 15.")
        self.state_machine.set_resolved(match_id, home_goals, away_goals)
        return IngestResult(match_id=match_id, home_goals=home_goals, away_goals=away_goals)

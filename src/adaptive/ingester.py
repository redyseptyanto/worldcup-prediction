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
    winner: str | None = None


class ResultIngester:
    """Validate and apply real match results."""

    def __init__(self, state_machine: MatchStateMachine) -> None:
        self.state_machine = state_machine

    def ingest(self, match_id: str, home_goals: int, away_goals: int, winner: str | None = None) -> IngestResult:
        match = self.state_machine.get(match_id)
        if match is None:
            raise KeyError(f"Unknown match id: {match_id}")
        if match["state"] == "RESOLVED":
            raise ValueError(f"Match {match_id} has already been ingested.")
        if match.get("home_team") in {None, "", "TBD"} or match.get("away_team") in {None, "", "TBD"}:
            raise ValueError(f"Match {match_id} participants are not locked yet.")
        if not (0 <= home_goals <= 15 and 0 <= away_goals <= 15):
            raise ValueError("Goals must be between 0 and 15.")
        if home_goals == away_goals and match.get("stage") != "group":
            if winner not in {match["home_team"], match["away_team"]}:
                raise ValueError(
                    f"Knockout draw for {match_id} requires winner to be one of {match['home_team']} or {match['away_team']}."
                )
        elif winner is not None:
            expected_winner = match["home_team"] if home_goals > away_goals else match["away_team"] if away_goals > home_goals else None
            if expected_winner is not None and winner != expected_winner:
                raise ValueError(f"Winner {winner} does not match the scoreline for {match_id}.")
        resolved_winner = winner
        if resolved_winner is None and home_goals != away_goals:
            resolved_winner = match["home_team"] if home_goals > away_goals else match["away_team"]
        self.state_machine.set_resolved(match_id, home_goals, away_goals, winner=resolved_winner)
        return IngestResult(match_id=match_id, home_goals=home_goals, away_goals=away_goals, winner=resolved_winner)

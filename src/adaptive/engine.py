"""Adaptive engine orchestration."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.adaptive.cascade import CascadeAnalyzer
from src.adaptive.comparer import SnapshotComparer
from src.adaptive.ingester import ResultIngester
from src.adaptive.rollback import RollbackManager
from src.adaptive.snapshotter import SnapshotManager
from src.adaptive.state_machine import MatchStateMachine
from src.config import TEAM_FEATURES_FILE
from src.models.train import load_or_train_ensemble, train_models
from src.simulation.tournament import TournamentSimulator
from src.utils.helpers import load_json


class AdaptiveEngine:
    """Coordinate ingest, re-simulation, and snapshots."""

    def __init__(self, iterations: int = 500) -> None:
        self.iterations = iterations
        self.state_machine = MatchStateMachine()
        self.ingester = ResultIngester(self.state_machine)
        self.cascade = CascadeAnalyzer(self.state_machine)
        self.snapshot_manager = SnapshotManager()
        self.comparer = SnapshotComparer()
        self.rollback_manager = RollbackManager(self.snapshot_manager, self.state_machine)

    def create_baseline_snapshot(self) -> str:
        if self.snapshot_manager.list_snapshots():
            return self.snapshot_manager.list_snapshots()[0]
        simulator = TournamentSimulator(iterations=self.iterations)
        output = simulator.run(resolved_results=self.state_machine.resolved_results())
        team_features = load_json(TEAM_FEATURES_FILE, default=[])
        return self.snapshot_manager.create_snapshot("baseline", output, self.state_machine._state, team_features)  # noqa: SLF001

    def ingest_result(self, match_id: str, home_goals: int, away_goals: int) -> dict[str, Any]:
        self.create_baseline_snapshot()
        ingest_result = self.ingester.ingest(match_id, home_goals, away_goals)
        train_models(force=True)
        simulator = TournamentSimulator(iterations=self.iterations)
        output = simulator.run(resolved_results=self.state_machine.resolved_results())
        team_features = load_json(TEAM_FEATURES_FILE, default=[])
        descriptor = f"after_{match_id.lower()}"
        snapshot_id = self.snapshot_manager.create_snapshot(descriptor, output, self.state_machine._state, team_features)  # noqa: SLF001
        return {
            "ingested": ingest_result.__dict__,
            "affected_matches": self.cascade.get_affected_matches(match_id),
            "snapshot_id": snapshot_id,
        }

    def ingest_batch(self, results: list[dict[str, int | str]]) -> dict[str, Any]:
        snapshots = []
        for row in results:
            response = self.ingest_result(
                match_id=str(row["match_id"]),
                home_goals=int(row["home_goals"]),
                away_goals=int(row["away_goals"]),
            )
            snapshots.append(response["snapshot_id"])
        return {"snapshots": snapshots, "count": len(results)}

    def tournament_status(self) -> dict[str, Any]:
        simulator = TournamentSimulator(iterations=max(100, self.iterations // 2))
        current = simulator.run(resolved_results=self.state_machine.resolved_results())
        return {
            "matches": self.state_machine.list_matches(),
            "standings": current["group_stage"]["standings"],
            "champion_odds": current["knockout"]["champion_odds"],
        }

    def compare_snapshots(self, from_snapshot: str, to_snapshot: str) -> dict[str, Any]:
        from_payload = {
            "bracket_data": self.snapshot_manager.read_snapshot(from_snapshot, "bracket_data.json"),
        }
        to_payload = {
            "bracket_data": self.snapshot_manager.read_snapshot(to_snapshot, "bracket_data.json"),
        }
        comparison = self.comparer.compare(from_snapshot, to_snapshot, from_payload, to_payload)
        self.comparer.write_report(comparison)
        return comparison

    def rollback_to(self, snapshot_id: str) -> dict[str, Any]:
        response = self.rollback_manager.rollback_to(snapshot_id)
        simulator = TournamentSimulator(iterations=self.iterations)
        output = simulator.run(resolved_results=self.state_machine.resolved_results())
        team_features = load_json(TEAM_FEATURES_FILE, default=[])
        rolled_back_snapshot = self.snapshot_manager.create_snapshot(
            f"rolled_back_from_{snapshot_id}",
            output,
            self.state_machine._state,  # noqa: SLF001
            team_features,
        )
        response["new_snapshot_id"] = rolled_back_snapshot
        return response

    def ingest_csv(self, file_path: str) -> dict[str, Any]:
        frame = pd.read_csv(file_path)
        return self.ingest_batch(frame.to_dict(orient="records"))

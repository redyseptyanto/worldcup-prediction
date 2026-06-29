"""Adaptive engine orchestration."""

from __future__ import annotations

import copy
from typing import Any

import pandas as pd

from src.adaptive.cascade import CascadeAnalyzer
from src.adaptive.comparer import SnapshotComparer
from src.adaptive.ingester import ResultIngester
from src.adaptive.rollback import RollbackManager
from src.adaptive.snapshotter import SnapshotManager
from src.adaptive.state_machine import MatchStateMachine
from src.config import ROSTERS_FILE, TEAM_FEATURES_FILE
from src.models.train import current_model_metadata, load_or_train_ensemble, train_models
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

    def _snapshot_payloads(self) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
        team_features = load_json(TEAM_FEATURES_FILE, default=[])
        rosters = load_json(ROSTERS_FILE, default={})
        model_metadata = current_model_metadata()
        return team_features, rosters, model_metadata

    def _snapshot_details(self) -> list[dict[str, Any]]:
        """Return snapshot metadata with backward-compatible fallback."""

        if hasattr(self.snapshot_manager, "list_snapshot_details"):
            return self.snapshot_manager.list_snapshot_details()
        return [
            {
                "snapshot_id": snapshot_id,
                "descriptor": snapshot_id.split("_", 1)[-1],
                "created_at": None,
                "resolved_matches": [],
                "model_metadata": {},
            }
            for snapshot_id in self.snapshot_manager.list_snapshots()
        ]

    def _sync_state_from_output(self, output: dict[str, Any]) -> None:
        self.state_machine.sync_knockout_matches(output)

    def create_baseline_snapshot(self) -> str:
        snapshot_details = self._snapshot_details()
        baseline_snapshot = next((detail for detail in snapshot_details if detail["descriptor"] == "baseline"), None)
        simulator = TournamentSimulator(iterations=self.iterations)
        output = simulator.run(resolved_results=self.state_machine.resolved_results())
        self._sync_state_from_output(output)
        team_features, rosters, model_metadata = self._snapshot_payloads()
        if baseline_snapshot and not baseline_snapshot["resolved_matches"]:
            existing_signature = (baseline_snapshot.get("model_metadata") or {}).get("signature")
            if existing_signature != model_metadata["signature"]:
                return self.snapshot_manager.update_snapshot(
                    baseline_snapshot["snapshot_id"],
                    output,
                    self.state_machine._state,  # noqa: SLF001
                    team_features,
                    rosters,
                    model_metadata,
                )
            return baseline_snapshot["snapshot_id"]
        return self.snapshot_manager.create_snapshot(
            "baseline",
            output,
            self.state_machine._state,  # noqa: SLF001
            team_features,
            rosters,
            model_metadata,
        )

    def ingest_result(self, match_id: str, home_goals: int, away_goals: int, winner: str | None = None) -> dict[str, Any]:
        self.create_baseline_snapshot()
        ingest_result = self.ingester.ingest(match_id, home_goals, away_goals, winner=winner)
        train_models(force=True)
        simulator = TournamentSimulator(iterations=self.iterations)
        output = simulator.run(resolved_results=self.state_machine.resolved_results())
        self._sync_state_from_output(output)
        team_features, rosters, model_metadata = self._snapshot_payloads()
        descriptor = f"after_{match_id.lower()}"
        snapshot_id = self.snapshot_manager.create_snapshot(
            descriptor,
            output,
            self.state_machine._state,  # noqa: SLF001
            team_features,
            rosters,
            model_metadata,
        )
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
                winner=None if pd.isna(row.get("winner")) else str(row.get("winner")),
            )
            snapshots.append(response["snapshot_id"])
        return {"snapshots": snapshots, "count": len(results)}

    def build_snapshot_from_results_file(
        self,
        file_path: str,
        descriptor: str = "after_group_stage_complete",
        refresh_official_data: bool = True,
    ) -> dict[str, Any]:
        """Create or refresh one comparison snapshot from a CSV of resolved results."""

        from src.data.fifa_official import refresh_official_fifa_data

        baseline_snapshot_id = self.create_baseline_snapshot()
        baseline_state = self.snapshot_manager.read_snapshot(baseline_snapshot_id, "state.json")
        if baseline_state is None:
            raise FileNotFoundError(f"Baseline snapshot {baseline_snapshot_id} does not contain state.json.")

        original_state = copy.deepcopy(self.state_machine._state)  # noqa: SLF001
        existing_snapshot = next((detail for detail in self._snapshot_details() if detail["descriptor"] == descriptor), None)
        frame = pd.read_csv(file_path, comment="#").dropna(subset=["match_id"])

        try:
            if refresh_official_data:
                refresh_official_fifa_data()

            self.state_machine.reset(snapshot_state=baseline_state)
            ingested_results: list[dict[str, Any]] = []
            for row in frame.itertuples(index=False):
                ingest_result = self.ingester.ingest(
                    match_id=str(row.match_id),
                    home_goals=int(row.home_goals),
                    away_goals=int(row.away_goals),
                    winner=None if pd.isna(getattr(row, "winner", None)) else str(getattr(row, "winner")),
                )
                ingested_results.append(ingest_result.__dict__)

            train_models(force=True)
            simulator = TournamentSimulator(iterations=self.iterations)
            output = simulator.run(resolved_results=self.state_machine.resolved_results())
            self._sync_state_from_output(output)
            team_features, rosters, model_metadata = self._snapshot_payloads()

            if existing_snapshot is not None:
                snapshot_id = self.snapshot_manager.update_snapshot(
                    existing_snapshot["snapshot_id"],
                    output,
                    self.state_machine._state,  # noqa: SLF001
                    team_features,
                    rosters,
                    model_metadata,
                )
            else:
                snapshot_id = self.snapshot_manager.create_snapshot(
                    descriptor,
                    output,
                    self.state_machine._state,  # noqa: SLF001
                    team_features,
                    rosters,
                    model_metadata,
                )
        finally:
            self.state_machine.reset(snapshot_state=original_state)

        return {
            "baseline_snapshot": baseline_snapshot_id,
            "snapshot_id": snapshot_id,
            "matches_ingested": len(frame),
            "ingested": ingested_results,
        }

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
        self._sync_state_from_output(output)
        team_features, rosters, model_metadata = self._snapshot_payloads()
        rolled_back_snapshot = self.snapshot_manager.create_snapshot(
            f"rolled_back_from_{snapshot_id}",
            output,
            self.state_machine._state,  # noqa: SLF001
            team_features,
            rosters,
            model_metadata,
        )
        response["new_snapshot_id"] = rolled_back_snapshot
        return response

    def refresh_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        snapshot_state = self.snapshot_manager.read_snapshot(snapshot_id, "state.json")
        if snapshot_state is None:
            raise FileNotFoundError(f"Snapshot {snapshot_id} does not exist.")
        original_state = copy.deepcopy(self.state_machine._state)  # noqa: SLF001
        try:
            self.state_machine.reset(snapshot_state=snapshot_state)
            simulator = TournamentSimulator(iterations=self.iterations)
            output = simulator.run(resolved_results=self.state_machine.resolved_results())
            self._sync_state_from_output(output)
            team_features, rosters, model_metadata = self._snapshot_payloads()
            updated_snapshot_id = self.snapshot_manager.update_snapshot(
                snapshot_id,
                output,
                self.state_machine._state,  # noqa: SLF001
                team_features,
                rosters,
                model_metadata,
            )
        finally:
            self.state_machine.reset(snapshot_state=original_state)
        return {"snapshot_id": updated_snapshot_id, "model_metadata": model_metadata}

    def ingest_csv(self, file_path: str) -> dict[str, Any]:
        frame = pd.read_csv(file_path)
        return self.ingest_batch(frame.to_dict(orient="records"))

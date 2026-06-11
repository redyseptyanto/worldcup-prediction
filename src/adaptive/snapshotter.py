"""Snapshot creation and listing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config import LEDGER_FILE, SETTINGS
from src.utils.helpers import load_json, save_json, utc_timestamp


class SnapshotManager:
    """Persist immutable tournament snapshots."""

    def __init__(self) -> None:
        self.snapshot_root = SETTINGS.snapshots_dir
        self.snapshot_root.mkdir(parents=True, exist_ok=True)

    def list_snapshots(self) -> list[str]:
        return sorted(path.name for path in self.snapshot_root.iterdir() if path.is_dir())

    def _next_snapshot_dir(self, descriptor: str) -> Path:
        existing = self.list_snapshots()
        next_index = len(existing)
        name = f"{next_index:03d}_{descriptor}"
        return self.snapshot_root / name

    def create_snapshot(
        self,
        descriptor: str,
        simulation_output: dict[str, Any],
        state: dict[str, Any],
        team_features: list[dict[str, Any]],
    ) -> str:
        snapshot_dir = self._next_snapshot_dir(descriptor)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_id = snapshot_dir.name
        save_json(
            snapshot_dir / "snapshot.json",
            {
                "snapshot_id": snapshot_id,
                "created_at": utc_timestamp(),
                "resolved_matches": [match_id for match_id, row in state.items() if row["state"] == "RESOLVED"],
            },
        )
        save_json(snapshot_dir / "predictions.json", simulation_output["predictions"])
        save_json(snapshot_dir / "bracket_data.json", simulation_output["knockout"])
        save_json(snapshot_dir / "standings.json", simulation_output["group_stage"]["standings"])
        save_json(snapshot_dir / "team_features.json", team_features)
        save_json(snapshot_dir / "state.json", state)
        save_json(snapshot_dir / "config.json", {"iterations": simulation_output["iterations"]})
        self._append_to_ledger(snapshot_id, simulation_output["predictions"], state)
        return snapshot_id

    def read_snapshot(self, snapshot_id: str, file_name: str) -> Any:
        return load_json(self.snapshot_root / snapshot_id / file_name)

    def _append_to_ledger(self, snapshot_id: str, predictions: list[dict[str, Any]], state: dict[str, Any]) -> None:
        ledger_columns = [
            "snapshot_id",
            "match_id",
            "predicted_home_goals",
            "predicted_away_goals",
            "predicted_winner",
            "predicted_home_win_pct",
            "predicted_draw_pct",
            "predicted_away_win_pct",
            "confidence_score",
            "actual_home_goals",
            "actual_away_goals",
            "correct_outcome",
        ]
        existing = pd.read_csv(LEDGER_FILE) if LEDGER_FILE.exists() else pd.DataFrame(columns=ledger_columns)
        rows = []
        for prediction in predictions:
            match_state = state.get(prediction["match_id"], {})
            predicted_winner = "home_win"
            best_prob = prediction["home_win_probability"]
            if prediction["draw_probability"] > best_prob:
                predicted_winner = "draw"
                best_prob = prediction["draw_probability"]
            if prediction["away_win_probability"] > best_prob:
                predicted_winner = "away_win"
            actual_winner = None
            if match_state.get("home_goals") is not None and match_state.get("away_goals") is not None:
                if match_state["home_goals"] > match_state["away_goals"]:
                    actual_winner = "home_win"
                elif match_state["home_goals"] == match_state["away_goals"]:
                    actual_winner = "draw"
                else:
                    actual_winner = "away_win"
            rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "match_id": prediction["match_id"],
                    "predicted_home_goals": prediction["predicted_home_goals"],
                    "predicted_away_goals": prediction["predicted_away_goals"],
                    "predicted_winner": predicted_winner,
                    "predicted_home_win_pct": prediction["home_win_probability"],
                    "predicted_draw_pct": prediction["draw_probability"],
                    "predicted_away_win_pct": prediction["away_win_probability"],
                    "confidence_score": prediction["confidence"],
                    "actual_home_goals": match_state.get("home_goals"),
                    "actual_away_goals": match_state.get("away_goals"),
                    "correct_outcome": actual_winner == predicted_winner if actual_winner else None,
                }
            )
        new_rows = pd.DataFrame(rows)
        combined = new_rows if existing.empty else pd.concat([existing, new_rows], ignore_index=True)
        combined.to_csv(LEDGER_FILE, index=False)

"""Accuracy summary helpers."""

from __future__ import annotations

import pandas as pd

from src.config import LEDGER_FILE
from src.visualization.snapshot_store import load_snapshot_file


def accuracy_summary(snapshot_id: str | None = None) -> dict[str, float]:
    """Return a simple accuracy summary for the selected snapshot."""

    if snapshot_id is not None:
        predictions = load_snapshot_file("predictions.json", snapshot_id=snapshot_id, default=[])
        state = load_snapshot_file("state.json", snapshot_id=snapshot_id, default={})
        if not predictions or not state:
            return {"resolved_predictions": 0.0, "outcome_accuracy": 0.0}
        rows = []
        for prediction in predictions:
            match_state = state.get(prediction["match_id"], {})
            if match_state.get("home_goals") is None or match_state.get("away_goals") is None:
                continue
            predicted_winner = "home_win"
            best_prob = prediction["home_win_probability"]
            if prediction["draw_probability"] > best_prob:
                predicted_winner = "draw"
                best_prob = prediction["draw_probability"]
            if prediction["away_win_probability"] > best_prob:
                predicted_winner = "away_win"
            actual_winner = (
                "home_win"
                if match_state["home_goals"] > match_state["away_goals"]
                else "away_win"
                if match_state["away_goals"] > match_state["home_goals"]
                else "draw"
            )
            rows.append(predicted_winner == actual_winner)
        if not rows:
            return {"resolved_predictions": 0.0, "outcome_accuracy": 0.0}
        accuracy = sum(rows) / len(rows)
        return {"resolved_predictions": float(len(rows)), "outcome_accuracy": round(float(accuracy), 4)}

    if not LEDGER_FILE.exists():
        return {"resolved_predictions": 0.0, "outcome_accuracy": 0.0}
    frame = pd.read_csv(LEDGER_FILE)
    resolved = frame.dropna(subset=["correct_outcome"])
    if resolved.empty:
        return {"resolved_predictions": 0.0, "outcome_accuracy": 0.0}
    accuracy = float(resolved["correct_outcome"].astype(bool).mean())
    return {"resolved_predictions": float(len(resolved)), "outcome_accuracy": round(accuracy, 4)}

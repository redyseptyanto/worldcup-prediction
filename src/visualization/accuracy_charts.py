"""Accuracy summary helpers."""

from __future__ import annotations

import pandas as pd

from src.config import LEDGER_FILE


def accuracy_summary() -> dict[str, float]:
    """Return a simple accuracy summary from the prediction ledger."""

    if not LEDGER_FILE.exists():
        return {"resolved_predictions": 0.0, "outcome_accuracy": 0.0}
    frame = pd.read_csv(LEDGER_FILE)
    resolved = frame.dropna(subset=["correct_outcome"])
    if resolved.empty:
        return {"resolved_predictions": 0.0, "outcome_accuracy": 0.0}
    accuracy = float(resolved["correct_outcome"].astype(bool).mean())
    return {"resolved_predictions": float(len(resolved)), "outcome_accuracy": round(accuracy, 4)}

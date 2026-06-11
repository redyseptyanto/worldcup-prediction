"""Probability table helpers."""

from __future__ import annotations

import pandas as pd

from src.config import PREDICTIONS_FILE


def probability_table() -> list[dict[str, object]]:
    """Return the latest prediction table."""

    if not PREDICTIONS_FILE.exists():
        return []
    return pd.read_csv(PREDICTIONS_FILE).to_dict(orient="records")

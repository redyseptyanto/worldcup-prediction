"""Load queued auto-results from the offline sample file."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.config import AUTO_RESULTS_FILE


def fetch_available_results(now: datetime | None = None) -> list[dict[str, object]]:
    """Return any auto-results whose availability timestamp has passed."""

    if not AUTO_RESULTS_FILE.exists():
        return []
    now = now or datetime.now(timezone.utc)
    frame = pd.read_csv(AUTO_RESULTS_FILE)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    ready = frame[frame["available_at"] <= now]
    return ready[["match_id", "home_goals", "away_goals"]].to_dict(orient="records")

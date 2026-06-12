"""Load raw and processed project data."""

from __future__ import annotations

import argparse
from typing import Any

import pandas as pd

from src.config import (
    LEDGER_FILE,
    MATCH_STATE_FILE,
    RAW_FIXTURES_FILE,
    RAW_MATCHES_FILE,
    RAW_RANKINGS_FILE,
    ensure_directories,
)
from src.data.collector import ensure_sample_data
from src.data.preprocessors import clean_fixtures, clean_historical_matches
from src.utils.constants import MATCH_STATE_PENDING
from src.utils.helpers import load_json, save_json
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)


def load_historical_matches() -> pd.DataFrame:
    """Load and clean historical results."""

    ensure_sample_data()
    frame = pd.read_csv(RAW_MATCHES_FILE)
    return clean_historical_matches(frame)


def load_rankings() -> pd.DataFrame:
    """Load seed ranking metadata."""

    ensure_sample_data()
    return pd.read_csv(RAW_RANKINGS_FILE)


def load_fixtures() -> pd.DataFrame:
    """Load upcoming group-stage fixtures."""

    ensure_sample_data()
    frame = pd.read_csv(RAW_FIXTURES_FILE)
    return clean_fixtures(frame)


def load_penalties() -> pd.DataFrame:
    """Load historical penalty data."""
    
    from src.config import RAW_PENALTIES_FILE
    if not RAW_PENALTIES_FILE.exists():
        return pd.DataFrame(columns=["team", "shootouts_won", "shootouts_lost", "penalty_win_rate"])
    return pd.read_csv(RAW_PENALTIES_FILE)


def load_official_rosters() -> pd.DataFrame:
    """Load scraped official rosters if available."""
    
    from src.config import SETTINGS
    rosters_file = SETTINGS.raw_dir / "players" / "official_2026_rosters.csv"
    if not rosters_file.exists():
        return pd.DataFrame(columns=["team", "player_name", "name_norm"])
    return pd.read_csv(rosters_file)


def initialize_state_store() -> dict[str, Any]:
    """Create file-backed state and ledger stores used by the baseline."""

    ensure_directories()
    fixtures = load_fixtures()
    if not MATCH_STATE_FILE.exists():
        payload = {
            row.match_id: {
                "match_id": row.match_id,
                "date": row.date.isoformat(),
                "stage": row.stage,
                "group": row.group,
                "home_team": row.home_team,
                "away_team": row.away_team,
                "state": MATCH_STATE_PENDING,
                "home_goals": None,
                "away_goals": None,
            }
            for row in fixtures.itertuples(index=False)
        }
        save_json(MATCH_STATE_FILE, payload)
    if not LEDGER_FILE.exists():
        pd.DataFrame(
            columns=[
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
        ).to_csv(LEDGER_FILE, index=False)
    LOGGER.info("Initialized file-backed state store.")
    return load_json(MATCH_STATE_FILE, default={})


def get_state_store() -> dict[str, Any]:
    """Return the current match state dictionary."""

    if not MATCH_STATE_FILE.exists():
        initialize_state_store()
    return load_json(MATCH_STATE_FILE, default={})


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Data loader utilities.")
    parser.add_argument("--init-db", action="store_true", help="Initialize file-backed state store.")
    args = parser.parse_args()
    if args.init_db:
        initialize_state_store()
        return
    load_historical_matches()
    load_rankings()
    load_fixtures()


if __name__ == "__main__":
    main()

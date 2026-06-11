"""Feature build orchestration."""

from __future__ import annotations

import argparse
import pandas as pd

from src.config import FIXTURE_CONTEXT_FILE, TEAM_FEATURES_FILE, TRAIN_DATASET_FILE, ensure_directories
from src.data.collector import ensure_sample_data
from src.data.loaders import load_fixtures, load_historical_matches, load_rankings
from src.features.external_features import build_fixture_context, build_macro_features
from src.features.history_features import build_training_dataset
from src.features.player_features import build_player_factor_features
from src.features.team_features import compute_team_summary
from src.utils.helpers import save_json
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)


def build_feature_artifacts() -> tuple[str, str]:
    """Build and persist processed training artifacts."""

    ensure_directories()
    ensure_sample_data()
    matches = load_historical_matches()
    rankings = load_rankings()
    fixtures = load_fixtures()
    training_df = build_training_dataset(matches, rankings)
    player_factors = build_player_factor_features()
    macro_factors = build_macro_features()
    tournament_teams = sorted(set(fixtures["home_team"]) | set(fixtures["away_team"]))
    team_summary = compute_team_summary(
        matches,
        rankings,
        player_factors=player_factors,
        macro_factors=macro_factors,
        output_teams=set(tournament_teams),
    )
    fixture_context = build_fixture_context()
    training_df.to_csv(TRAIN_DATASET_FILE, index=False)
    save_json(TEAM_FEATURES_FILE, team_summary.to_dict(orient="records"))
    save_json(FIXTURE_CONTEXT_FILE, fixture_context)
    LOGGER.info("Built feature artifacts.")
    return str(TRAIN_DATASET_FILE), str(TEAM_FEATURES_FILE)


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Build feature artifacts.")
    parser.parse_args()
    build_feature_artifacts()


if __name__ == "__main__":
    main()

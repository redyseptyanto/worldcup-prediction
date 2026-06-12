import pandas as pd

from src.config import TEAM_FEATURES_FILE, TRAIN_DATASET_FILE
from src.features.build_features import build_feature_artifacts
from src.utils.helpers import load_json


def test_build_feature_artifacts_outputs_expected_columns() -> None:
    build_feature_artifacts()
    training_data = pd.read_csv(TRAIN_DATASET_FILE)
    team_features = load_json(TEAM_FEATURES_FILE, default=[])

    assert {
        "elo_diff",
        "ranking_diff",
        "form_diff",
        "outcome",
        "world_cup_pedigree_diff",
        "world_cup_semi_final_rate_diff",
        "world_cup_appearances_diff",
    }.issubset(training_data.columns)
    teams = {row["team"] for row in team_features}
    assert {"Brazil", "England", "Mexico", "South Korea", "Turkey", "United States"}.issubset(teams)
    team_lookup = {row["team"]: row for row in team_features}
    assert {"world_cup_pedigree", "world_cup_semi_final_rate", "world_cup_appearances"}.issubset(team_lookup["France"])
    assert team_lookup["France"]["world_cup_pedigree"] > team_lookup.get("Curaçao", {}).get("world_cup_pedigree", 0.0)

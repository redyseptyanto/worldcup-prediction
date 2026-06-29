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
        "xg_for_diff",
        "xg_balance_diff",
        "world_cup_pedigree_diff",
        "world_cup_semi_final_rate_diff",
        "world_cup_appearances_diff",
    }.issubset(training_data.columns)
    teams = {row["team"] for row in team_features}
    assert {"Brazil", "England", "Mexico", "South Korea", "Turkey", "United States"}.issubset(teams)
    team_lookup = {row["team"]: row for row in team_features}
    assert {
        "world_cup_pedigree",
        "world_cup_semi_final_rate",
        "world_cup_appearances",
        "xg_for_avg",
        "xg_against_avg",
        "xg_balance",
    }.issubset(team_lookup["France"])
    assert team_lookup["France"]["world_cup_pedigree"] > team_lookup.get("Cura\u00e7ao", {}).get(
        "world_cup_pedigree",
        0.0,
    )


def test_build_feature_artifacts_merges_official_tournament_form(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.features.build_features.load_official_tournament_form",
        lambda: pd.DataFrame(
            [
                {
                    "team": "France",
                    "official_group": "I",
                    "official_group_position": 1,
                    "tournament_matches_played": 3,
                    "tournament_points_pct": 1.0,
                    "tournament_goal_diff_per_match": 1.333,
                    "tournament_goals_for_per_match": 2.0,
                    "tournament_goals_against_per_match": 0.667,
                    "tournament_wins_per_match": 1.0,
                    "tournament_conduct_score": 3.0,
                    "tournament_qualified": 1.0,
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "src.features.build_features.load_official_team_stats_features",
        lambda: pd.DataFrame(),
    )

    build_feature_artifacts()
    team_features = load_json(TEAM_FEATURES_FILE, default=[])
    france = next(row for row in team_features if row["team"] == "France")
    australia = next(row for row in team_features if row["team"] == "Australia")

    assert france["official_group"] == "I"
    assert france["official_group_position"] == 1
    assert france["tournament_points_pct"] == 1.0
    assert australia["tournament_points_pct"] == 0.0


def test_build_feature_artifacts_merges_official_team_stats_features(monkeypatch) -> None:
    monkeypatch.setattr("src.features.build_features.load_official_tournament_form", lambda: pd.DataFrame())
    monkeypatch.setattr(
        "src.features.build_features.load_official_team_stats_features",
        lambda: pd.DataFrame(
            [
                {
                    "team": "France",
                    "official_stats_matches_played": 3.0,
                    "official_stats_weight": 0.3,
                    "official_attack_index": 0.5,
                    "official_distribution_index": 0.4,
                    "official_defense_index": 0.3,
                    "official_goalkeeping_index": 0.1,
                    "official_discipline_index": 0.2,
                    "official_movement_index": 0.25,
                    "official_physical_index": 0.15,
                    "official_xg_signal": 0.45,
                    "official_attack_signal": 0.4,
                    "official_defense_signal": 0.3,
                    "official_control_signal": 0.32,
                    "official_recent_form_index": 0.38,
                }
            ]
        ),
    )

    build_feature_artifacts()
    team_features = load_json(TEAM_FEATURES_FILE, default=[])
    france = next(row for row in team_features if row["team"] == "France")
    australia = next(row for row in team_features if row["team"] == "Australia")

    assert france["official_stats_weight"] == 0.3
    assert france["official_recent_form_index"] == 0.38
    assert france["attack_strength"] != france["base_attack_strength"]
    assert australia["official_stats_weight"] == 0.0

import pandas as pd

from src.models.poisson_model import PoissonModel


def test_poisson_model_blends_goal_rate_and_xg_rate() -> None:
    matches = pd.DataFrame(
        [
            {"home_goals": 2, "away_goals": 1},
            {"home_goals": 1, "away_goals": 1},
        ]
    )
    team_features = pd.DataFrame(
        [
            {
                "team": "Alpha",
                "attack_strength": 1.5,
                "defense_strength": 1.1,
                "xg_for_avg": 2.0,
                "xg_against_avg": 0.9,
            },
            {
                "team": "Beta",
                "attack_strength": 1.5,
                "defense_strength": 1.1,
                "xg_for_avg": 1.0,
                "xg_against_avg": 1.8,
            },
        ]
    )

    model = PoissonModel()
    model.fit(matches, team_features)
    prediction = model.predict_match("Alpha", "Beta")

    assert prediction["home_goals"] > prediction["away_goals"]
    assert prediction["home_win"] > prediction["away_win"]


def test_poisson_model_falls_back_when_xg_columns_are_missing() -> None:
    matches = pd.DataFrame(
        [
            {"home_goals": 1, "away_goals": 0},
            {"home_goals": 2, "away_goals": 1},
        ]
    )
    team_features = pd.DataFrame(
        [
            {"team": "Home", "attack_strength": 1.7, "defense_strength": 1.0},
            {"team": "Away", "attack_strength": 1.2, "defense_strength": 1.3},
        ]
    )

    model = PoissonModel()
    model.fit(matches, team_features)
    prediction = model.predict_match("Home", "Away")

    assert prediction["home_goals"] > prediction["away_goals"]
    assert prediction["home_win"] > prediction["away_win"]

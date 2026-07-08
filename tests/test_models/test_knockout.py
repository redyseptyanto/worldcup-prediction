from __future__ import annotations

from typing import Any

import pandas as pd

from src.models.knockout import KnockoutBlendedModel, KnockoutCalibratedModel


class StubBaseModel:
    def predict_match(self, home_team: str, away_team: str, match_id: str | None = None) -> dict[str, Any]:
        return {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "features": {
                "elo_diff": 120.0,
                "home_penalty_win_rate": 0.58,
                "away_penalty_win_rate": 0.42,
            },
            "outcome_probabilities": {
                "home_win": 0.74,
                "draw": 0.16,
                "away_win": 0.10,
            },
            "predicted_score": {"home": 3, "away": 0},
            "most_likely_exact_score": {"home": 3, "away": 0, "probability": 0.14},
            "confidence": {"overall": 84.0, "label": "High"},
            "expected_goals": {"home": 2.6, "away": 0.35},
            "contextual_factors": {},
        }


def test_knockout_calibrated_model_changes_knockout_predictions_only() -> None:
    model = KnockoutCalibratedModel(StubBaseModel())

    group_prediction = model.predict_match("Home", "Away", match_id="GRP-A-M1")
    knockout_prediction = model.predict_match("Home", "Away", match_id="R32-1")

    assert group_prediction["outcome_probabilities"] == {
        "home_win": 0.74,
        "draw": 0.16,
        "away_win": 0.10,
    }
    assert group_prediction["predicted_score"] == {"home": 3, "away": 0}

    assert knockout_prediction["outcome_probabilities"]["draw"] < 0.16
    assert knockout_prediction["outcome_probabilities"]["home_win"] < 0.74
    assert knockout_prediction["expected_goals"] == {"home": 2.0, "away": 0.5}
    assert knockout_prediction["predicted_score"] == {"home": 1, "away": 0}
    assert knockout_prediction["score_model"] == "knockout_calibrated_poisson"


def test_knockout_blended_model_uses_history_fallback_and_changes_score_profile() -> None:
    tournament_form = pd.DataFrame(
        [
            {
                "team": "Home",
                "tournament_goals_for_per_match": 2.4,
                "tournament_goals_against_per_match": 0.8,
            },
            {
                "team": "Away",
                "tournament_goals_for_per_match": 1.0,
                "tournament_goals_against_per_match": 1.7,
            },
        ]
    )
    historical_matches = pd.DataFrame(
        [
            {"home_team": "Home", "away_team": "Away", "home_goals": 2, "away_goals": 1, "stage": "historical", "round": "historical"},
            {"home_team": "Home", "away_team": "Other", "home_goals": 3, "away_goals": 1, "stage": "historical", "round": "historical"},
            {"home_team": "Other", "away_team": "Away", "home_goals": 1, "away_goals": 0, "stage": "historical", "round": "historical"},
            {"home_team": "Away", "away_team": "Home", "home_goals": 1, "away_goals": 2, "stage": "historical", "round": "historical"},
        ]
    )

    calibrated = KnockoutCalibratedModel(StubBaseModel()).predict_match("Home", "Away", match_id="R32-1")
    blended_model = KnockoutBlendedModel(
        StubBaseModel(),
        tournament_form=tournament_form,
        historical_matches=historical_matches,
    )
    blended = blended_model.predict_match("Home", "Away", match_id="R32-1")

    assert blended_model.history_scope == "all_matches_fallback"
    assert blended["score_model"] == "knockout_calibrated_form_history_blend"
    assert blended["expected_goals"]["home"] > calibrated["expected_goals"]["home"]
    assert blended["expected_goals"]["away"] > calibrated["expected_goals"]["away"]
    assert blended["predicted_score"] != calibrated["predicted_score"]

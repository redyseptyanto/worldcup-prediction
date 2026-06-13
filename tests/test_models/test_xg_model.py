import pandas as pd

from src.models.xg_model import XGOutcomeModel


def test_xg_model_predicts_probabilities_that_sum_to_one() -> None:
    training_data = pd.DataFrame(
        [
            {
                "xg_for_diff": 0.8,
                "xg_against_diff": -0.4,
                "xg_balance_diff": 1.2,
                "xg_overperformance_diff": 0.2,
                "xg_defensive_overperformance_diff": 0.1,
                "outcome": "home_win",
            },
            {
                "xg_for_diff": -0.5,
                "xg_against_diff": 0.3,
                "xg_balance_diff": -0.8,
                "xg_overperformance_diff": -0.1,
                "xg_defensive_overperformance_diff": -0.2,
                "outcome": "away_win",
            },
            {
                "xg_for_diff": 0.1,
                "xg_against_diff": 0.0,
                "xg_balance_diff": 0.1,
                "xg_overperformance_diff": 0.0,
                "xg_defensive_overperformance_diff": 0.0,
                "outcome": "draw",
            },
        ]
        * 10
    )
    model = XGOutcomeModel()
    model.fit(training_data)

    probabilities = model.predict_proba(
        {
            "xg_for_diff": 0.4,
            "xg_against_diff": -0.2,
            "xg_balance_diff": 0.6,
            "xg_overperformance_diff": 0.1,
            "xg_defensive_overperformance_diff": 0.05,
        }
    )

    assert round(sum(probabilities.values()), 6) == 1.0
    assert set(probabilities) == {"home_win", "draw", "away_win"}

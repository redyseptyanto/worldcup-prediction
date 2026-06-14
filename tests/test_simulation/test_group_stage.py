import numpy as np
import pandas as pd

from src.data.loaders import load_fixtures
from src.models.train import load_or_train_ensemble
from src.simulation.group_stage import simulate_group_matches, simulate_group_stage


def test_group_stage_handles_resolved_matches() -> None:
    fixtures = load_fixtures()
    group_a = fixtures[fixtures["group"] == "A"]
    model = load_or_train_ensemble(force=True)
    ranking, predictions = simulate_group_matches(
        group_a,
        model,
        np.random.default_rng(42),
        resolved_results={"GRP-A-M1": {"home_goals": 2, "away_goals": 0}},
    )

    assert len(predictions) == 6
    assert ranking[0]["team"] in {"Czech Republic", "Mexico", "South Africa", "South Korea"}
    assert any(row["result_source"] == "resolved" for row in predictions)


class StubGroupStageModel:
    def __init__(self, predictions: dict[str, dict[str, object]]) -> None:
        self.predictions = predictions

    def predict_match(self, home_team: str, away_team: str, match_id: str | None = None) -> dict[str, object]:
        if match_id is None:
            raise ValueError("match_id is required for this stub")
        return self.predictions[match_id]


def test_group_stage_standings_match_combined_probability_signal() -> None:
    fixtures = pd.DataFrame(
        [
            {"match_id": "G1", "date": "2026-06-01T00:00:00Z", "group": "C", "home_team": "Brazil", "away_team": "Morocco"},
            {"match_id": "G2", "date": "2026-06-02T00:00:00Z", "group": "C", "home_team": "Haiti", "away_team": "Scotland"},
            {"match_id": "G3", "date": "2026-06-03T00:00:00Z", "group": "C", "home_team": "Scotland", "away_team": "Morocco"},
            {"match_id": "G4", "date": "2026-06-04T00:00:00Z", "group": "C", "home_team": "Brazil", "away_team": "Haiti"},
            {"match_id": "G5", "date": "2026-06-05T00:00:00Z", "group": "C", "home_team": "Scotland", "away_team": "Brazil"},
            {"match_id": "G6", "date": "2026-06-06T00:00:00Z", "group": "C", "home_team": "Morocco", "away_team": "Haiti"},
        ]
    )
    fixtures["date"] = pd.to_datetime(fixtures["date"], utc=True)

    default_prediction = {
        "outcome_probabilities": {"home_win": 0.4, "draw": 0.3, "away_win": 0.3},
        "confidence": {"overall": 60.0, "label": "Moderate"},
        "expected_goals": {"home": 1.2, "away": 1.1},
    }
    model = StubGroupStageModel(
        {
            "G1": {**default_prediction, "predicted_score": {"home": 1, "away": 1}},
            "G2": {**default_prediction, "predicted_score": {"home": 2, "away": 1}},
            "G3": {**default_prediction, "predicted_score": {"home": 1, "away": 2}},
            "G4": {**default_prediction, "predicted_score": {"home": 2, "away": 1}},
            "G5": {**default_prediction, "predicted_score": {"home": 1, "away": 2}},
            "G6": {**default_prediction, "predicted_score": {"home": 2, "away": 1}},
        }
    )

    results = simulate_group_stage(fixtures, model, iterations=3, seed=42)
    group_c = results["standings"]["C"]

    assert group_c[0]["team"] == "Brazil"
    assert group_c[0]["points"] == 4.2
    assert (group_c[0]["wins"], group_c[0]["draws"], group_c[0]["losses"]) == (1.1, 0.9, 1)
    assert group_c[1]["team"] == "Scotland"
    assert results["predictions"]["C"][0]["result_source"] == "signal_projected"

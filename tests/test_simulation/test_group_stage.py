import numpy as np

from src.data.loaders import load_fixtures
from src.models.train import load_or_train_ensemble
from src.simulation.group_stage import simulate_group_matches


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

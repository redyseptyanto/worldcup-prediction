import pandas as pd

from src.simulation.stage_reach import build_projected_opponents_table, estimate_stage_reach_probabilities


def test_stage_reach_aggregation_uses_simulated_paths(monkeypatch) -> None:
    fixtures = pd.DataFrame(
        {
            "home_team": ["A1", "A2", "A3"],
            "away_team": ["B1", "B2", "B3"],
        }
    )

    def fake_simulation(*_args, **_kwargs) -> dict[str, object]:
        return {
            "group_rankings": {
                "A": [{"team": "A1"}, {"team": "A2"}, {"team": "A3"}],
                "B": [{"team": "B1"}, {"team": "B2"}, {"team": "B3"}],
            },
            "best_third": [{"team": "A3", "group": "A"}, {"team": "B3", "group": "B"}],
            "round_of_32_pairings": [
                {"home_team": "A1", "away_team": "B3"},
                {"home_team": "B1", "away_team": "A3"},
            ],
            "round_of_16_pairings": [{"home_team": "A1", "away_team": "B1"}],
            "quarter_final_pairings": [{"home_team": "A1", "away_team": "A2"}],
            "semi_final_pairings": [{"home_team": "A1", "away_team": "B2"}],
            "third_place_pairing": [{"home_team": "A2", "away_team": "B2"}],
            "final_pairing": [{"home_team": "A1", "away_team": "B1"}],
            "final_result": {"winner": "A1"},
        }

    monkeypatch.setattr("src.simulation.stage_reach.simulate_one_tournament", fake_simulation)

    result = estimate_stage_reach_probabilities(fixtures, model=None, iterations=2, seed=42)
    stage_probabilities = result.stage_probabilities.set_index("team")

    assert stage_probabilities.loc["A1", "finish_1"] == 1.0
    assert stage_probabilities.loc["A3", "best_third"] == 1.0
    assert stage_probabilities.loc["A1", "champion"] == 1.0
    assert result.round_of_32_opponents.loc["A1", "B3"] == 1.0
    assert result.round_of_16_opponents.loc["A1", "B1"] == 1.0
    assert result.quarter_final_opponents.loc["A1", "A2"] == 1.0
    assert result.semi_final_opponents.loc["A1", "B2"] == 1.0
    assert result.final_opponents.loc["A1", "B1"] == 1.0
    assert result.best_third_group_mix.set_index("group").loc["A", "share_of_best_third_slots"] == 0.125

    table = build_projected_opponents_table(result, "A1", top_n_per_stage=4)
    assert set(table["stage"]) == {"Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final"}
    assert float(table.loc[table["stage"] == "Final", "path_probability"].iloc[0]) == 1.0

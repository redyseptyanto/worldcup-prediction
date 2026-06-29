from __future__ import annotations

from typing import Any

import pandas as pd

from src.simulation.knockout_stage import resolve_round_of_32_pairings, simulate_knockout_stage


class StubKnockoutModel:
    def __init__(self, strengths: dict[str, float]) -> None:
        self.strengths = strengths

    def predict_match(self, home_team: str, away_team: str, match_id: str | None = None) -> dict[str, Any]:
        home_strength = self.strengths[home_team]
        away_strength = self.strengths[away_team]
        home_favored = home_strength >= away_strength
        probs = (
            {"home_win": 0.65, "draw": 0.2, "away_win": 0.15}
            if home_favored
            else {"home_win": 0.15, "draw": 0.2, "away_win": 0.65}
        )
        predicted_score = (
            {"home": 2, "away": 1}
            if home_favored
            else {"home": 1, "away": 2}
        )
        return {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "features": {
                "elo_diff": home_strength - away_strength,
                "home_penalty_win_rate": 0.5,
                "away_penalty_win_rate": 0.5,
            },
            "outcome_probabilities": probs,
            "predicted_score": predicted_score,
            "confidence": {"overall": 75.0, "label": "High"},
            "expected_goals": {
                "home": float(predicted_score["home"]),
                "away": float(predicted_score["away"]),
            },
            "contextual_factors": {},
        }


def test_knockout_bracket_uses_advancement_projection(monkeypatch) -> None:
    strengths = {f"Team {index}": float(100 - index) for index in range(1, 31)}
    strengths["Curaçao"] = 10.0
    strengths["France"] = 90.0
    model = StubKnockoutModel(strengths)

    pairings = [
        {"match_id": "R32-1", "annex_c": "M73", "home_team": "Team 1", "away_team": "Team 2", "home_path": "1A", "away_path": "2B"},
        {"match_id": "R32-2", "annex_c": "M74", "home_team": "Team 3", "away_team": "Team 4", "home_path": "1C", "away_path": "3D"},
        {"match_id": "R32-3", "annex_c": "M75", "home_team": "Team 5", "away_team": "Team 6", "home_path": "1E", "away_path": "2F"},
        {"match_id": "R32-4", "annex_c": "M76", "home_team": "Team 7", "away_team": "Team 8", "home_path": "1G", "away_path": "2H"},
        {"match_id": "R32-5", "annex_c": "M77", "home_team": "Team 9", "away_team": "Team 10", "home_path": "1I", "away_path": "3J"},
        {"match_id": "R32-6", "annex_c": "M78", "home_team": "Curaçao", "away_team": "France", "home_path": "2E", "away_path": "2I"},
        {"match_id": "R32-7", "annex_c": "M79", "home_team": "Team 11", "away_team": "Team 12", "home_path": "1K", "away_path": "3L"},
        {"match_id": "R32-8", "annex_c": "M80", "home_team": "Team 13", "away_team": "Team 14", "home_path": "1M", "away_path": "2N"},
        {"match_id": "R32-9", "annex_c": "M81", "home_team": "Team 15", "away_team": "Team 16", "home_path": "1O", "away_path": "3P"},
        {"match_id": "R32-10", "annex_c": "M82", "home_team": "Team 17", "away_team": "Team 18", "home_path": "1Q", "away_path": "3R"},
        {"match_id": "R32-11", "annex_c": "M83", "home_team": "Team 19", "away_team": "Team 20", "home_path": "2S", "away_path": "2T"},
        {"match_id": "R32-12", "annex_c": "M84", "home_team": "Team 21", "away_team": "Team 22", "home_path": "1U", "away_path": "2V"},
        {"match_id": "R32-13", "annex_c": "M85", "home_team": "Team 23", "away_team": "Team 24", "home_path": "1W", "away_path": "3X"},
        {"match_id": "R32-14", "annex_c": "M86", "home_team": "Team 25", "away_team": "Team 26", "home_path": "1Y", "away_path": "2Z"},
        {"match_id": "R32-15", "annex_c": "M87", "home_team": "Team 27", "away_team": "Team 28", "home_path": "1AA", "away_path": "3AB"},
        {"match_id": "R32-16", "annex_c": "M88", "home_team": "Team 29", "away_team": "Team 30", "home_path": "2AC", "away_path": "2AD"},
    ]

    monkeypatch.setattr(
        "src.simulation.knockout_stage.build_round_of_32",
        lambda _group_rankings: (pairings, []),
    )

    result = simulate_knockout_stage(model, group_rankings={}, iterations=5, seed=42)

    m78 = next(match for match in result["bracket"]["round_of_32"] if match["annex_c"] == "M78")
    assert m78["winner"] == "France"
    assert m78["score"] == {"home": 0, "away": 1}
    assert m78["advancement_method"] == "regulation"
    assert m78["prediction"]["advancement_probabilities"]["away"] > 0.7


def test_knockout_bracket_respects_resolved_results(monkeypatch) -> None:
    strengths = {"Home": 10.0, "Away": 90.0}
    for index in range(1, 31):
        strengths[f"Team {index}"] = float(80 - index)
    model = StubKnockoutModel(strengths)

    pairings = [{"match_id": "R32-1", "annex_c": "M73", "home_team": "Home", "away_team": "Away", "home_path": "1A", "away_path": "2B"}]
    for index in range(2, 17):
        pairings.append(
            {
                "match_id": f"R32-{index}",
                "annex_c": f"M{72 + index}",
                "home_team": f"Team {index * 2 - 3}",
                "away_team": f"Team {index * 2 - 2}",
                "home_path": f"slot{index}A",
                "away_path": f"slot{index}B",
            }
        )

    monkeypatch.setattr(
        "src.simulation.knockout_stage.build_round_of_32",
        lambda _group_rankings: (pairings, []),
    )

    result = simulate_knockout_stage(
        model,
        group_rankings={},
        iterations=5,
        seed=42,
        resolved_results={"R32-1": {"home_goals": 1, "away_goals": 0, "winner": "Home"}},
    )

    locked_match = next(match for match in result["bracket"]["round_of_32"] if match["match_id"] == "R32-1")
    assert locked_match["winner"] == "Home"
    assert locked_match["score"] == {"home": 1, "away": 0}
    assert locked_match["result_source"] == "resolved"


def test_knockout_projection_adjusts_score_to_match_advancement_signal(monkeypatch) -> None:
    class MismatchProjectionModel:
        def predict_match(self, home_team: str, away_team: str, match_id: str | None = None) -> dict[str, object]:
            return {
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "features": {
                    "elo_diff": 20.0,
                    "home_penalty_win_rate": 0.9,
                    "away_penalty_win_rate": 0.1,
                },
                "outcome_probabilities": {"home_win": 0.2, "draw": 0.5, "away_win": 0.3},
                "predicted_score": {"home": 1, "away": 2},
                "most_likely_exact_score": {"home": 1, "away": 1, "probability": 0.18},
                "confidence": {"overall": 62.0, "label": "Moderate"},
                "expected_goals": {"home": 1.2, "away": 1.1},
                "contextual_factors": {},
            }

        def _conditional_scoreline(self, expected_goals: dict[str, float], outcome: str) -> dict[str, int]:
            mapping = {
                "home_win": {"home": 1, "away": 0},
                "draw": {"home": 1, "away": 1},
                "away_win": {"home": 0, "away": 1},
            }
            return mapping[outcome]

    pairings = []
    for index in range(1, 17):
        pairings.append(
            {
                "match_id": f"R32-{index}",
                "annex_c": f"M{72 + index}",
                "home_team": f"Home {index}",
                "away_team": f"Away {index}",
                "home_path": f"slot{index}A",
                "away_path": f"slot{index}B",
            }
        )

    monkeypatch.setattr(
        "src.simulation.knockout_stage.build_round_of_32",
        lambda _group_rankings: (pairings, []),
    )

    result = simulate_knockout_stage(MismatchProjectionModel(), group_rankings={}, iterations=2, seed=42)
    projected_match = next(match for match in result["bracket"]["round_of_32"] if match["match_id"] == "R32-1")

    assert projected_match["winner"] == "Home 1"
    assert projected_match["score"] == {"home": 1, "away": 1}
    assert projected_match["advancement_method"] == "penalties"


def test_round_of_32_uses_official_fifa_bracket_only_after_full_group_resolution(monkeypatch) -> None:
    baseline_pairings = [
        {
            "match_id": "R32-1",
            "annex_c": "M73",
            "round": "round_of_32",
            "home_team": "Baseline Home",
            "away_team": "Baseline Away",
            "home_path": "2A",
            "away_path": "2B",
        }
    ]
    official_round_of_32 = pd.DataFrame(
        [
            {
                "annex_c": f"M{72 + index}",
                "match_number": 72 + index,
                "date": "",
                "home_team": f"Official Home {index}",
                "away_team": f"Official Away {index}",
                "home_path": f"H{index}",
                "away_path": f"A{index}",
            }
            for index in range(1, 17)
        ]
    )

    monkeypatch.setattr(
        "src.simulation.knockout_stage.build_round_of_32",
        lambda _group_rankings: (baseline_pairings, [{"team": "Baseline Third", "group": "A"}]),
    )
    monkeypatch.setattr(
        "src.simulation.knockout_stage.load_official_round_of_32",
        lambda: official_round_of_32,
    )
    monkeypatch.setattr(
        "src.simulation.knockout_stage.load_official_best_third",
        lambda: [{"team": "Official Third", "group": "A"}],
    )

    unresolved_pairings, unresolved_best_third = resolve_round_of_32_pairings(
        {},
        resolved_results={f"GRP-{index}": {"home_goals": 1, "away_goals": 0} for index in range(1, 71)},
    )
    resolved_pairings, resolved_best_third = resolve_round_of_32_pairings(
        {},
        resolved_results={f"GRP-{index}": {"home_goals": 1, "away_goals": 0} for index in range(1, 73)},
    )

    official_m73 = next(match for match in resolved_pairings if match["annex_c"] == "M73")

    assert unresolved_pairings == baseline_pairings
    assert unresolved_best_third == [{"team": "Baseline Third", "group": "A"}]
    assert official_m73["home_team"] == "Official Home 1"
    assert official_m73["away_team"] == "Official Away 1"
    assert resolved_best_third == [{"team": "Official Third", "group": "A"}]

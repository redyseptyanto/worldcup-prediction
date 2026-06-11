"""Group-stage simulation for the full 48-team tournament."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from src.models.ensemble import EnsembleModel


def _empty_standings() -> dict[str, dict[str, float]]:
    return defaultdict(
        lambda: {
            "points": 0.0,
            "goal_difference": 0.0,
            "goals_for": 0.0,
            "goals_against": 0.0,
            "played": 0.0,
        }
    )


def _apply_result(standings: dict[str, dict[str, float]], home_team: str, away_team: str, home_goals: int, away_goals: int) -> None:
    home = standings[home_team]
    away = standings[away_team]
    home["played"] += 1
    away["played"] += 1
    home["goals_for"] += home_goals
    home["goals_against"] += away_goals
    away["goals_for"] += away_goals
    away["goals_against"] += home_goals
    home["goal_difference"] += home_goals - away_goals
    away["goal_difference"] += away_goals - home_goals
    if home_goals > away_goals:
        home["points"] += 3
    elif away_goals > home_goals:
        away["points"] += 3
    else:
        home["points"] += 1
        away["points"] += 1


def rank_group(standings: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    """Return teams ordered by points, goal difference, and goals scored."""

    ranked = []
    for team, metrics in standings.items():
        ranked.append(
            {
                "team": team,
                "points": int(metrics["points"]),
                "goal_difference": int(metrics["goal_difference"]),
                "goals_for": int(metrics["goals_for"]),
                "goals_against": int(metrics["goals_against"]),
                "played": int(metrics["played"]),
            }
        )
    return sorted(
        ranked,
        key=lambda row: (row["points"], row["goal_difference"], row["goals_for"], row["team"]),
        reverse=True,
    )


def rank_third_placed_teams(group_rankings: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Rank third-placed teams across all groups using tournament tiebreakers."""

    third_placed_rows = []
    for group_id, ranking in group_rankings.items():
        third_row = ranking[2].copy()
        third_row["group"] = group_id
        third_placed_rows.append(third_row)
    return sorted(
        third_placed_rows,
        key=lambda row: (row["points"], row["goal_difference"], row["goals_for"], row["team"]),
        reverse=True,
    )


def simulate_group_matches(
    group_fixtures: pd.DataFrame,
    model: EnsembleModel,
    rng: np.random.Generator,
    resolved_results: dict[str, dict[str, int]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Simulate one group's fixtures and return standings plus match summaries."""

    resolved_results = resolved_results or {}
    standings = _empty_standings()
    predictions: list[dict[str, Any]] = []

    for row in group_fixtures.sort_values(["date", "match_id"]).itertuples(index=False):
        prediction = model.predict_match(row.home_team, row.away_team, match_id=row.match_id)
        if row.match_id in resolved_results:
            home_goals = int(resolved_results[row.match_id]["home_goals"])
            away_goals = int(resolved_results[row.match_id]["away_goals"])
            source = "resolved"
        else:
            home_goals = int(rng.poisson(prediction["expected_goals"]["home"]))
            away_goals = int(rng.poisson(prediction["expected_goals"]["away"]))
            source = "simulated"
        _apply_result(standings, row.home_team, row.away_team, home_goals, away_goals)
        predictions.append(
            {
                "match_id": row.match_id,
                "group": row.group,
                "home_team": row.home_team,
                "away_team": row.away_team,
                "predicted_score": prediction["predicted_score"],
                "outcome_probabilities": prediction["outcome_probabilities"],
                "confidence": prediction["confidence"],
                "simulated_result": {"home": home_goals, "away": away_goals},
                "result_source": source,
            }
        )

    return rank_group(standings), predictions


def simulate_group_stage(
    fixtures: pd.DataFrame,
    model: EnsembleModel,
    iterations: int,
    seed: int = 42,
    resolved_results: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Run repeated group-stage simulations and estimate qualification odds."""

    rng = np.random.default_rng(seed)
    qualification_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    sampled_predictions: dict[str, list[dict[str, Any]]] = {}
    latest_rankings: dict[str, list[dict[str, Any]]] = {}
    latest_best_third: list[dict[str, Any]] = []

    for _ in range(iterations):
        current_rankings: dict[str, list[dict[str, Any]]] = {}
        current_predictions: dict[str, list[dict[str, Any]]] = {}

        for group_id, group_fixtures in fixtures.groupby("group"):
            ranking, predictions = simulate_group_matches(group_fixtures, model, rng, resolved_results=resolved_results)
            current_rankings[group_id] = ranking
            current_predictions[group_id] = predictions
            for position, row in enumerate(ranking, start=1):
                qualification_counts[row["team"]][f"finish_{position}"] += 1

        best_third = rank_third_placed_teams(current_rankings)[:8]
        qualified_third_teams = {row["team"] for row in best_third}

        for ranking in current_rankings.values():
            for position, row in enumerate(ranking, start=1):
                if position <= 2 or row["team"] in qualified_third_teams:
                    qualification_counts[row["team"]]["qualify"] += 1

        latest_rankings = current_rankings
        sampled_predictions = current_predictions
        latest_best_third = best_third

    qualification_probabilities = {
        team: {
            label: round(count / iterations, 4)
            for label, count in metrics.items()
        }
        for team, metrics in qualification_counts.items()
    }
    return {
        "standings": latest_rankings,
        "predictions": sampled_predictions,
        "qualification_probabilities": qualification_probabilities,
        "best_third_placed": latest_best_third,
    }

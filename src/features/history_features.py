"""History-based feature engineering."""

from __future__ import annotations

from collections import defaultdict, deque

import pandas as pd

from src.features.world_cup_pedigree import build_world_cup_pedigree_history, summarize_world_cup_pedigree


def build_training_dataset(matches: pd.DataFrame, rankings: pd.DataFrame) -> pd.DataFrame:
    """Build a time-aware training dataset from historical matches."""

    elo = {row.team: float(row.seed_rating) for row in rankings.itertuples(index=False)}
    ranking_points = {row.team: float(row.ranking_points) for row in rankings.itertuples(index=False)}
    scored: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=8))
    conceded: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=8))
    results: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=5))
    pedigree_history = build_world_cup_pedigree_history(matches)

    rows: list[dict[str, object]] = []

    for row in matches.sort_values("date").itertuples(index=False):
        pedigree_snapshot = summarize_world_cup_pedigree(pedigree_history, as_of=pd.Timestamp(row.date))
        home_pedigree = pedigree_snapshot.get(
            row.home_team,
            {
                "world_cup_pedigree": 0.0,
                "world_cup_semi_final_rate": 0.0,
                "world_cup_appearances": 0.0,
            },
        )
        away_pedigree = pedigree_snapshot.get(
            row.away_team,
            {
                "world_cup_pedigree": 0.0,
                "world_cup_semi_final_rate": 0.0,
                "world_cup_appearances": 0.0,
            },
        )
        home_scored = list(scored[row.home_team])
        away_scored = list(scored[row.away_team])
        home_conceded = list(conceded[row.home_team])
        away_conceded = list(conceded[row.away_team])
        home_results = list(results[row.home_team])
        away_results = list(results[row.away_team])

        def average(values: list[int], fallback: float) -> float:
            return float(sum(values) / len(values)) if values else fallback

        features = {
            "match_id": row.match_id,
            "date": row.date,
            "home_team": row.home_team,
            "away_team": row.away_team,
            "home_goals": row.home_goals,
            "away_goals": row.away_goals,
            "elo_diff": elo[row.home_team] - elo[row.away_team],
            "ranking_diff": ranking_points[row.home_team] - ranking_points[row.away_team],
            "goals_for_diff": average(home_scored, 1.4) - average(away_scored, 1.4),
            "goals_against_diff": average(home_conceded, 1.1) - average(away_conceded, 1.1),
            "form_diff": average(home_results, 1.4) - average(away_results, 1.4),
            "attack_diff": average(home_scored, 1.4) - average(away_conceded, 1.1),
            "defense_diff": average(home_conceded, 1.1) - average(away_scored, 1.4),
            "world_cup_pedigree_diff": home_pedigree["world_cup_pedigree"] - away_pedigree["world_cup_pedigree"],
            "world_cup_semi_final_rate_diff": home_pedigree["world_cup_semi_final_rate"] - away_pedigree["world_cup_semi_final_rate"],
            "world_cup_appearances_diff": home_pedigree["world_cup_appearances"] - away_pedigree["world_cup_appearances"],
        }
        outcome = "home_win" if row.home_goals > row.away_goals else "draw" if row.home_goals == row.away_goals else "away_win"
        features["outcome"] = outcome
        rows.append(features)

        home_points = 3 if row.home_goals > row.away_goals else 1 if row.home_goals == row.away_goals else 0
        away_points = 3 if row.away_goals > row.home_goals else 1 if row.home_goals == row.away_goals else 0
        scored[row.home_team].append(int(row.home_goals))
        scored[row.away_team].append(int(row.away_goals))
        conceded[row.home_team].append(int(row.away_goals))
        conceded[row.away_team].append(int(row.home_goals))
        results[row.home_team].append(home_points)
        results[row.away_team].append(away_points)

        expected_home = 1.0 / (1.0 + 10 ** ((elo[row.away_team] - elo[row.home_team]) / 400.0))
        actual_home = 1.0 if row.home_goals > row.away_goals else 0.5 if row.home_goals == row.away_goals else 0.0
        k_factor = 22
        elo[row.home_team] += k_factor * (actual_home - expected_home)
        elo[row.away_team] -= k_factor * (actual_home - expected_home)

    return pd.DataFrame(rows)

"""Team-level feature engineering."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd


def compute_team_summary(
    matches: pd.DataFrame,
    rankings: pd.DataFrame,
    player_factors: pd.DataFrame | None = None,
    macro_factors: pd.DataFrame | None = None,
    output_teams: set[str] | None = None,
) -> pd.DataFrame:
    """Compute current team-level summary metrics from historical matches."""

    stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "matches": 0.0,
            "goals_for": 0.0,
            "goals_against": 0.0,
            "points": 0.0,
        }
    )
    elo: dict[str, float] = {row.team: float(row.seed_rating) for row in rankings.itertuples(index=False)}

    for row in matches.itertuples(index=False):
        home_points = 3 if row.home_goals > row.away_goals else 1 if row.home_goals == row.away_goals else 0
        away_points = 3 if row.away_goals > row.home_goals else 1 if row.home_goals == row.away_goals else 0
        home = stats[row.home_team]
        away = stats[row.away_team]
        home["matches"] += 1
        away["matches"] += 1
        home["goals_for"] += row.home_goals
        home["goals_against"] += row.away_goals
        away["goals_for"] += row.away_goals
        away["goals_against"] += row.home_goals
        home["points"] += home_points
        away["points"] += away_points

        expected_home = 1.0 / (1.0 + 10 ** ((elo[row.away_team] - elo[row.home_team]) / 400.0))
        actual_home = 1.0 if row.home_goals > row.away_goals else 0.5 if row.home_goals == row.away_goals else 0.0
        k_factor = 22
        elo[row.home_team] += k_factor * (actual_home - expected_home)
        elo[row.away_team] -= k_factor * (actual_home - expected_home)

    summary_rows = []
    for row in rankings.itertuples(index=False):
        if output_teams is not None and row.team not in output_teams:
            continue
        team_stats = stats[row.team]
        matches_played = max(team_stats["matches"], 1.0)
        goals_for = team_stats["goals_for"] / matches_played
        goals_against = team_stats["goals_against"] / matches_played
        points = team_stats["points"] / matches_played
        summary_rows.append(
            {
                "team": row.team,
                "group": row.group,
                "ranking_points": row.ranking_points,
                "elo": round(elo[row.team], 2),
                "goals_for_avg": round(goals_for, 3),
                "goals_against_avg": round(goals_against, 3),
                "form_points_avg": round(points, 3),
                "attack_strength": round(max(0.35, goals_for), 3),
                "defense_strength": round(max(0.35, goals_against), 3),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("team").reset_index(drop=True)
    if player_factors is not None and not player_factors.empty:
        summary = summary.merge(player_factors, on="team", how="left")
    if macro_factors is not None and not macro_factors.empty:
        summary = summary.merge(macro_factors, on="team", how="left")
        
    # Merge penalty features
    from src.data.loaders import load_penalties
    penalties = load_penalties()
    if not penalties.empty:
        summary = summary.merge(penalties[["team", "penalty_win_rate"]], on="team", how="left")
        summary["penalty_win_rate"] = summary["penalty_win_rate"].fillna(0.5)
    else:
        summary["penalty_win_rate"] = 0.5
        
    return summary

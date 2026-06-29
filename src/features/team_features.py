"""Team-level feature engineering."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd

from src.features.world_cup_pedigree import build_world_cup_pedigree_history, summarize_world_cup_pedigree


def compute_team_summary(
    matches: pd.DataFrame,
    rankings: pd.DataFrame,
    xg_matches: pd.DataFrame | None = None,
    player_factors: pd.DataFrame | None = None,
    macro_factors: pd.DataFrame | None = None,
    tournament_form_factors: pd.DataFrame | None = None,
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
    pedigree_summary = summarize_world_cup_pedigree(build_world_cup_pedigree_history(matches))
    xg_stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "matches": 0.0,
            "xg_for": 0.0,
            "xg_against": 0.0,
            "goals_for": 0.0,
            "goals_against": 0.0,
        }
    )
    if xg_matches is not None and not xg_matches.empty:
        for row in xg_matches.itertuples(index=False):
            home = xg_stats[row.home_team]
            away = xg_stats[row.away_team]
            home["matches"] += 1
            away["matches"] += 1
            home["xg_for"] += float(row.home_xg)
            home["xg_against"] += float(row.away_xg)
            away["xg_for"] += float(row.away_xg)
            away["xg_against"] += float(row.home_xg)
            home["goals_for"] += float(row.home_goals)
            home["goals_against"] += float(row.away_goals)
            away["goals_for"] += float(row.away_goals)
            away["goals_against"] += float(row.home_goals)
    for row in rankings.itertuples(index=False):
        if output_teams is not None and row.team not in output_teams:
            continue
        team_stats = stats[row.team]
        team_xg_stats = xg_stats[row.team]
        pedigree = pedigree_summary.get(
            row.team,
            {
                "world_cup_pedigree": 0.0,
                "world_cup_semi_final_rate": 0.0,
                "world_cup_appearances": 0.0,
            },
        )
        matches_played = max(team_stats["matches"], 1.0)
        goals_for = team_stats["goals_for"] / matches_played
        goals_against = team_stats["goals_against"] / matches_played
        points = team_stats["points"] / matches_played
        xg_matches_played = max(team_xg_stats["matches"], 1.0)
        if team_xg_stats["matches"] > 0:
            xg_for_avg = team_xg_stats["xg_for"] / xg_matches_played
            xg_against_avg = team_xg_stats["xg_against"] / xg_matches_played
            xg_overperformance = (team_xg_stats["goals_for"] - team_xg_stats["xg_for"]) / xg_matches_played
            xg_defensive_overperformance = (team_xg_stats["xg_against"] - team_xg_stats["goals_against"]) / xg_matches_played
        else:
            xg_for_avg = goals_for
            xg_against_avg = goals_against
            xg_overperformance = 0.0
            xg_defensive_overperformance = 0.0
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
                "world_cup_pedigree": pedigree["world_cup_pedigree"],
                "world_cup_semi_final_rate": pedigree["world_cup_semi_final_rate"],
                "world_cup_appearances": pedigree["world_cup_appearances"],
                "xg_for_avg": round(xg_for_avg, 3),
                "xg_against_avg": round(xg_against_avg, 3),
                "xg_balance": round(xg_for_avg - xg_against_avg, 3),
                "xg_overperformance": round(xg_overperformance, 3),
                "xg_defensive_overperformance": round(xg_defensive_overperformance, 3),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("team").reset_index(drop=True)
    if player_factors is not None and not player_factors.empty:
        summary = summary.merge(player_factors, on="team", how="left")
    if macro_factors is not None and not macro_factors.empty:
        summary = summary.merge(macro_factors, on="team", how="left")
    if tournament_form_factors is not None and not tournament_form_factors.empty:
        summary = summary.merge(tournament_form_factors, on="team", how="left")
        summary["official_group"] = summary["official_group"].fillna(summary["group"])
        for column, default in {
            "official_group_position": 0.0,
            "tournament_matches_played": 0.0,
            "tournament_points_pct": 0.0,
            "tournament_goal_diff_per_match": 0.0,
            "tournament_goals_for_per_match": 0.0,
            "tournament_goals_against_per_match": 0.0,
            "tournament_wins_per_match": 0.0,
            "tournament_conduct_score": 0.0,
            "tournament_qualified": 0.0,
        }.items():
            summary[column] = summary[column].fillna(default)

    # Merge penalty features
    from src.data.loaders import load_penalties

    penalties = load_penalties()
    if not penalties.empty:
        summary = summary.merge(penalties[["team", "penalty_win_rate"]], on="team", how="left")
        summary["penalty_win_rate"] = summary["penalty_win_rate"].fillna(0.5)
    else:
        summary["penalty_win_rate"] = 0.5

    return summary

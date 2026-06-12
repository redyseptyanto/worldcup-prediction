"""World Cup-only pedigree features shared across pipelines."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

WORLD_CUP_NAME = "FIFA World Cup"
_TOURNAMENT_MATCH_COUNT = 64
_STAGE_SEQUENCE = (
    ["group"] * 48
    + ["round_of_16"] * 8
    + ["quarter_final"] * 4
    + ["semi_final"] * 2
    + ["third_place"] * 1
    + ["final"] * 1
)
_RECENCY_WEIGHTS = {
    0: 1.0,
    4: 0.75,
    8: 0.55,
    12: 0.4,
}


def _normalize_world_cup_tournaments(matches: pd.DataFrame) -> pd.DataFrame:
    """Return completed World Cup tournaments with inferred stage labels."""

    if matches.empty or "tournament" not in matches:
        return pd.DataFrame()

    world_cup = matches.loc[matches["tournament"].eq(WORLD_CUP_NAME)].copy()
    if world_cup.empty:
        return pd.DataFrame()

    world_cup["tournament_year"] = pd.to_datetime(world_cup["date"], utc=True, errors="coerce").dt.year
    normalized_frames: list[pd.DataFrame] = []

    for _, tournament in world_cup.groupby("tournament_year", sort=True):
        ordered = tournament.sort_values(["date", "match_id"]).reset_index(drop=True)
        if len(ordered) != _TOURNAMENT_MATCH_COUNT:
            continue
        ordered["world_cup_stage"] = _STAGE_SEQUENCE
        normalized_frames.append(ordered)

    if not normalized_frames:
        return pd.DataFrame()
    return pd.concat(normalized_frames, ignore_index=True)


def build_world_cup_pedigree_history(matches: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    """Build per-team World Cup pedigree history from completed tournaments."""

    world_cup = _normalize_world_cup_tournaments(matches)
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if world_cup.empty:
        return {}

    for year, tournament in world_cup.groupby("tournament_year", sort=True):
        finish_date = pd.Timestamp(tournament["date"].max())
        final_match = tournament.loc[tournament["world_cup_stage"] == "final"].iloc[0]
        champion = final_match["home_team"] if final_match["home_goals"] > final_match["away_goals"] else final_match["away_team"]
        runner_up = final_match["away_team"] if champion == final_match["home_team"] else final_match["home_team"]

        teams = set(tournament["home_team"]) | set(tournament["away_team"])
        for team in teams:
            team_matches = tournament[(tournament["home_team"] == team) | (tournament["away_team"] == team)]
            stages = set(team_matches["world_cup_stage"])

            if team == champion:
                finish_score = 5.0
            elif team == runner_up:
                finish_score = 4.0
            elif "semi_final" in stages or "third_place" in stages:
                finish_score = 3.0
            elif "quarter_final" in stages:
                finish_score = 2.0
            elif "round_of_16" in stages:
                finish_score = 1.0
            else:
                finish_score = 0.0

            history[team].append(
                {
                    "tournament_year": int(year),
                    "finish_date": finish_date,
                    "finish_score": finish_score,
                    "semi_final_reached": 1.0 if finish_score >= 3.0 else 0.0,
                }
            )

    return {team: sorted(entries, key=lambda entry: entry["finish_date"]) for team, entries in history.items()}


def _recency_weight(reference_year: int, tournament_year: int) -> float:
    year_gap = max(0, reference_year - tournament_year)
    if year_gap in _RECENCY_WEIGHTS:
        return _RECENCY_WEIGHTS[year_gap]
    cycles = max(0, year_gap // 4)
    return max(0.2, 0.75 ** cycles)


def summarize_world_cup_pedigree(
    history: dict[str, list[dict[str, Any]]],
    as_of: pd.Timestamp | None = None,
) -> dict[str, dict[str, float]]:
    """Summarize World Cup pedigree for each team as of a point in time."""

    if not history:
        return {}

    reference_year = int(as_of.year) if as_of is not None else max(
        entry["tournament_year"] for entries in history.values() for entry in entries
    )
    summary: dict[str, dict[str, float]] = {}

    for team, entries in history.items():
        eligible = [
            entry
            for entry in entries
            if as_of is None or entry["finish_date"] < as_of
        ]
        if not eligible:
            summary[team] = {
                "world_cup_pedigree": 0.0,
                "world_cup_semi_final_rate": 0.0,
                "world_cup_appearances": 0.0,
            }
            continue

        weights = [_recency_weight(reference_year, entry["tournament_year"]) for entry in eligible]
        total_weight = sum(weights) or 1.0
        pedigree = sum(weight * (entry["finish_score"] / 5.0) for weight, entry in zip(weights, eligible)) / total_weight
        semi_rate = sum(weight * entry["semi_final_reached"] for weight, entry in zip(weights, eligible)) / total_weight

        summary[team] = {
            "world_cup_pedigree": round(float(pedigree), 4),
            "world_cup_semi_final_rate": round(float(semi_rate), 4),
            "world_cup_appearances": float(len(eligible)),
        }

    return summary

"""Monte Carlo helpers for stage-reach probability analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.models.ensemble import EnsembleModel
from src.simulation.group_stage import simulate_group_matches
from src.simulation.knockout_stage import (
    FINAL_MATCH_NUMBER,
    R16_MATCH_NUMBERS,
    QF_MATCH_NUMBERS,
    SF_MATCH_NUMBERS,
    THIRD_PLACE_MATCH_NUMBER,
    _next_round_pairings,
    _play_round,
    build_round_of_32,
)

STAGE_COLUMNS = [
    "finish_1",
    "finish_2",
    "finish_3",
    "best_third",
    "reach_round_of_32",
    "reach_round_of_16",
    "reach_quarter_finals",
    "reach_semi_finals",
    "reach_third_place",
    "reach_final",
    "champion",
]


@dataclass(frozen=True)
class StageReachSimulation:
    stage_probabilities: pd.DataFrame
    round_of_32_opponents: pd.DataFrame
    best_third_group_mix: pd.DataFrame


def simulate_one_tournament(
    fixtures: pd.DataFrame,
    model: EnsembleModel,
    rng: np.random.Generator,
    resolved_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Simulate one full tournament path from groups through the final."""

    resolved_results = resolved_results or {}
    group_rankings: dict[str, list[dict[str, Any]]] = {}
    for group_id, group_fixtures in fixtures.groupby("group"):
        ranking, _ = simulate_group_matches(
            group_fixtures,
            model,
            rng,
            resolved_results=resolved_results,
        )
        group_rankings[group_id] = ranking

    round_of_32_pairings, best_third = build_round_of_32(group_rankings)
    round_of_32_results = _play_round(model, round_of_32_pairings, rng, resolved_results=resolved_results)

    round_of_16_pairings = _next_round_pairings(round_of_32_results, "R16", R16_MATCH_NUMBERS)
    round_of_16_results = _play_round(model, round_of_16_pairings, rng, resolved_results=resolved_results)

    quarter_final_pairings = _next_round_pairings(round_of_16_results, "QF", QF_MATCH_NUMBERS)
    quarter_final_results = _play_round(model, quarter_final_pairings, rng, resolved_results=resolved_results)

    semi_final_pairings = _next_round_pairings(quarter_final_results, "SF", SF_MATCH_NUMBERS)
    semi_final_results = _play_round(model, semi_final_pairings, rng, resolved_results=resolved_results)

    third_place_pairing = [
        {
            "match_id": "THIRD-1",
            "annex_c": THIRD_PLACE_MATCH_NUMBER,
            "round": "third_place",
            "home_team": semi_final_results[0]["loser"],
            "away_team": semi_final_results[1]["loser"],
        }
    ]
    third_place_result = _play_round(model, third_place_pairing, rng, resolved_results=resolved_results)[0]

    final_pairing = _next_round_pairings(semi_final_results, "FINAL", [FINAL_MATCH_NUMBER])
    final_result = _play_round(model, final_pairing, rng, resolved_results=resolved_results)[0]

    return {
        "group_rankings": group_rankings,
        "best_third": best_third,
        "round_of_32_pairings": round_of_32_pairings,
        "round_of_16_pairings": round_of_16_pairings,
        "quarter_final_pairings": quarter_final_pairings,
        "semi_final_pairings": semi_final_pairings,
        "third_place_pairing": third_place_pairing,
        "final_pairing": final_pairing,
        "third_place_result": third_place_result,
        "final_result": final_result,
    }


def estimate_stage_reach_probabilities(
    fixtures: pd.DataFrame,
    model: EnsembleModel,
    iterations: int,
    seed: int = 42,
    resolved_results: dict[str, dict[str, Any]] | None = None,
) -> StageReachSimulation:
    """Estimate stage-reach probabilities for every team."""

    resolved_results = resolved_results or {}
    rng = np.random.default_rng(seed)
    teams = sorted(set(fixtures["home_team"]) | set(fixtures["away_team"]))
    stage_counts: dict[str, Counter[str]] = defaultdict(Counter)
    round_of_32_opponent_counts: dict[str, Counter[str]] = defaultdict(Counter)
    best_third_group_counts: Counter[str] = Counter()

    for _ in range(iterations):
        simulation = simulate_one_tournament(fixtures, model, rng, resolved_results)

        for ranking in simulation["group_rankings"].values():
            for position, row in enumerate(ranking, start=1):
                stage_counts[row["team"]][f"finish_{position}"] += 1

        for row in simulation["best_third"]:
            stage_counts[row["team"]]["best_third"] += 1
            best_third_group_counts[row["group"]] += 1

        for match in simulation["round_of_32_pairings"]:
            home_team = match["home_team"]
            away_team = match["away_team"]
            stage_counts[home_team]["reach_round_of_32"] += 1
            stage_counts[away_team]["reach_round_of_32"] += 1
            round_of_32_opponent_counts[home_team][away_team] += 1
            round_of_32_opponent_counts[away_team][home_team] += 1

        for stage_name, pairings in [
            ("reach_round_of_16", simulation["round_of_16_pairings"]),
            ("reach_quarter_finals", simulation["quarter_final_pairings"]),
            ("reach_semi_finals", simulation["semi_final_pairings"]),
        ]:
            for match in pairings:
                stage_counts[match["home_team"]][stage_name] += 1
                stage_counts[match["away_team"]][stage_name] += 1

        third_place_match = simulation["third_place_pairing"][0]
        stage_counts[third_place_match["home_team"]]["reach_third_place"] += 1
        stage_counts[third_place_match["away_team"]]["reach_third_place"] += 1

        final_match = simulation["final_pairing"][0]
        stage_counts[final_match["home_team"]]["reach_final"] += 1
        stage_counts[final_match["away_team"]]["reach_final"] += 1
        stage_counts[simulation["final_result"]["winner"]]["champion"] += 1

    stage_records: list[dict[str, Any]] = []
    for team in teams:
        record = {"team": team}
        for column in STAGE_COLUMNS:
            record[column] = stage_counts[team][column] / iterations
        stage_records.append(record)

    stage_probabilities = pd.DataFrame(stage_records).sort_values(
        ["champion", "reach_final", "reach_semi_finals", "reach_round_of_16"],
        ascending=False,
    ).reset_index(drop=True)

    round_of_32_opponents = pd.DataFrame(0.0, index=teams, columns=teams)
    for team, opponent_counter in round_of_32_opponent_counts.items():
        for opponent, count in opponent_counter.items():
            round_of_32_opponents.loc[team, opponent] = count / iterations

    best_third_group_mix = pd.DataFrame(
        {
            "group": sorted(best_third_group_counts),
            "share_of_best_third_slots": [
                best_third_group_counts[group] / (iterations * 8)
                for group in sorted(best_third_group_counts)
            ],
        }
    ).sort_values("share_of_best_third_slots", ascending=False, ignore_index=True)

    return StageReachSimulation(
        stage_probabilities=stage_probabilities,
        round_of_32_opponents=round_of_32_opponents,
        best_third_group_mix=best_third_group_mix,
    )


def build_uncertain_round_of_32_paths(
    stage_probabilities: pd.DataFrame,
    round_of_32_opponents: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize how many possible round-of-32 opponents each team can draw."""

    return (
        (round_of_32_opponents > 0).sum(axis=1)
        .rename("possible_round_of_32_opponents")
        .to_frame()
        .join(stage_probabilities.set_index("team")[["reach_round_of_32", "reach_round_of_16", "champion"]])
        .query("reach_round_of_32 > 0")
        .sort_values(["possible_round_of_32_opponents", "reach_round_of_32"], ascending=[False, False])
    )


def show_round_of_32_opponents(
    round_of_32_opponents: pd.DataFrame,
    team: str,
    top_n: int = 16,
) -> pd.Series:
    """Return the most likely round-of-32 opponents for one team."""

    distribution = round_of_32_opponents.loc[team]
    return distribution[distribution > 0].sort_values(ascending=False).head(top_n)

"""Knockout bracket simulation for the 48-team tournament."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from src.config import RAW_THIRD_PLACE_MAPPING_FILE
from src.models.ensemble import EnsembleModel
from src.simulation.group_stage import rank_third_placed_teams
from src.simulation.penalties import pick_penalty_winner
from src.utils.helpers import load_json

ROUND_OF_32_TEMPLATE = [
    ("R32-1", "round_of_32", ("runner_up", "A"), ("runner_up", "B")),
    ("R32-2", "round_of_32", ("winner", "E"), ("third_slot", "E")),
    ("R32-3", "round_of_32", ("winner", "F"), ("runner_up", "C")),
    ("R32-4", "round_of_32", ("winner", "C"), ("runner_up", "F")),
    ("R32-5", "round_of_32", ("winner", "I"), ("third_slot", "I")),
    ("R32-6", "round_of_32", ("runner_up", "E"), ("runner_up", "I")),
    ("R32-7", "round_of_32", ("winner", "A"), ("third_slot", "A")),
    ("R32-8", "round_of_32", ("winner", "L"), ("third_slot", "L")),
    ("R32-9", "round_of_32", ("winner", "D"), ("third_slot", "D")),
    ("R32-10", "round_of_32", ("winner", "G"), ("third_slot", "G")),
    ("R32-11", "round_of_32", ("runner_up", "K"), ("runner_up", "L")),
    ("R32-12", "round_of_32", ("winner", "H"), ("runner_up", "J")),
    ("R32-13", "round_of_32", ("winner", "B"), ("third_slot", "B")),
    ("R32-14", "round_of_32", ("winner", "J"), ("runner_up", "H")),
    ("R32-15", "round_of_32", ("winner", "K"), ("third_slot", "K")),
    ("R32-16", "round_of_32", ("runner_up", "D"), ("runner_up", "G")),
]


def _team_from_reference(
    reference: tuple[str, str],
    group_rankings: dict[str, list[dict[str, Any]]],
    third_place_lookup: dict[str, str],
    third_place_slots: dict[str, str],
) -> str:
    reference_type, group_id = reference
    if reference_type == "winner":
        return group_rankings[group_id][0]["team"]
    if reference_type == "runner_up":
        return group_rankings[group_id][1]["team"]
    if reference_type == "third_slot":
        resolved_group = third_place_slots[group_id]
        return third_place_lookup[resolved_group]
    raise ValueError(f"Unsupported knockout reference: {reference_type}")


def build_round_of_32(group_rankings: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the official round-of-32 bracket, including best third-placed teams."""

    third_place_rankings = rank_third_placed_teams(group_rankings)
    qualified_third = third_place_rankings[:8]
    qualified_groups = tuple(sorted(row["group"] for row in qualified_third))
    third_place_lookup = {row["group"]: row["team"] for row in qualified_third}
    third_place_mappings = load_json(RAW_THIRD_PLACE_MAPPING_FILE, default={})
    third_place_slots = third_place_mappings["|".join(qualified_groups)]

    matches = []
    for match_id, round_name, home_ref, away_ref in ROUND_OF_32_TEMPLATE:
        matches.append(
            {
                "match_id": match_id,
                "round": round_name,
                "home_team": _team_from_reference(home_ref, group_rankings, third_place_lookup, third_place_slots),
                "away_team": _team_from_reference(away_ref, group_rankings, third_place_lookup, third_place_slots),
            }
        )
    return matches, qualified_third


def _resolve_knockout_match(model: EnsembleModel, home_team: str, away_team: str, rng: np.random.Generator, match_id: str) -> dict[str, Any]:
    prediction = model.predict_match(home_team, away_team, match_id=match_id)
    home_goals = int(rng.poisson(prediction["expected_goals"]["home"]))
    away_goals = int(rng.poisson(prediction["expected_goals"]["away"]))
    if home_goals == away_goals:
        winner = pick_penalty_winner(home_team, away_team, prediction["features"]["elo_diff"], rng)
    else:
        winner = home_team if home_goals > away_goals else away_team
    loser = away_team if winner == home_team else home_team
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "winner": winner,
        "loser": loser,
        "score": {"home": home_goals, "away": away_goals},
        "prediction": prediction,
    }


def _play_round(
    model: EnsembleModel,
    pairings: list[dict[str, Any]],
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    return [
        _resolve_knockout_match(model, pairing["home_team"], pairing["away_team"], rng, pairing["match_id"])
        for pairing in pairings
    ]


def _next_round_pairings(results: list[dict[str, Any]], round_prefix: str) -> list[dict[str, Any]]:
    pairings: list[dict[str, Any]] = []
    for index in range(0, len(results), 2):
        left = results[index]
        right = results[index + 1]
        pairings.append(
            {
                "match_id": f"{round_prefix}-{index // 2 + 1}",
                "round": round_prefix,
                "home_team": left["winner"],
                "away_team": right["winner"],
            }
        )
    return pairings


def simulate_knockout_stage(
    model: EnsembleModel,
    group_rankings: dict[str, list[dict[str, Any]]],
    iterations: int,
    seed: int = 42,
) -> dict[str, Any]:
    """Run the full 32-team knockout bracket."""

    rng = np.random.default_rng(seed)
    champion_counts: dict[str, int] = defaultdict(int)
    latest_bracket: dict[str, Any] = {}
    latest_best_third: list[dict[str, Any]] = []

    for _ in range(iterations):
        round_of_32_pairings, best_third = build_round_of_32(group_rankings)
        round_of_32 = _play_round(model, round_of_32_pairings, rng)
        round_of_16_pairings = _next_round_pairings(round_of_32, "R16")
        round_of_16 = _play_round(model, round_of_16_pairings, rng)
        quarter_pairings = _next_round_pairings(round_of_16, "QF")
        quarter_finals = _play_round(model, quarter_pairings, rng)
        semi_pairings = _next_round_pairings(quarter_finals, "SF")
        semi_finals = _play_round(model, semi_pairings, rng)
        third_place_pairing = [
            {
                "match_id": "THIRD-1",
                "round": "third_place",
                "home_team": semi_finals[0]["loser"],
                "away_team": semi_finals[1]["loser"],
            }
        ]
        third_place = _play_round(model, third_place_pairing, rng)[0]
        final_pairings = _next_round_pairings(semi_finals, "FINAL")
        final_result = _play_round(model, final_pairings, rng)[0]
        champion_counts[final_result["winner"]] += 1
        latest_best_third = best_third
        latest_bracket = {
            "round_of_32": round_of_32,
            "round_of_16": round_of_16,
            "quarter_finals": quarter_finals,
            "semi_finals": semi_finals,
            "third_place": third_place,
            "final": final_result,
        }

    champion_odds = {
        team: round(count / iterations, 4)
        for team, count in sorted(champion_counts.items(), key=lambda item: item[1], reverse=True)
    }
    return {
        "champion_odds": champion_odds,
        "best_third_placed": latest_best_third,
        "bracket": latest_bracket,
    }

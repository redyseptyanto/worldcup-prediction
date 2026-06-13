"""Knockout bracket simulation for the 48-team tournament."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from src.config import RAW_THIRD_PLACE_MAPPING_FILE
from src.models.ensemble import EnsembleModel
from src.simulation.group_stage import rank_third_placed_teams
from src.simulation.penalties import penalty_home_probability, pick_penalty_winner
from src.utils.helpers import load_json

# Each entry: (match_id, annex_c_number, round, home_ref, away_ref)
ROUND_OF_32_TEMPLATE = [
    # Left Top Branch (→ QF97 → SF101)
    ("R32-2",  "M74", "round_of_32", ("winner", "E"),     ("third_slot", "E")),
    ("R32-5",  "M77", "round_of_32", ("winner", "I"),     ("third_slot", "I")),
    ("R32-1",  "M73", "round_of_32", ("runner_up", "A"),  ("runner_up", "B")),
    ("R32-3",  "M75", "round_of_32", ("winner", "F"),     ("runner_up", "C")),

    # Left Bottom Branch (→ QF98 → SF101)
    ("R32-11", "M83", "round_of_32", ("runner_up", "K"),  ("runner_up", "L")),
    ("R32-12", "M84", "round_of_32", ("winner", "H"),     ("runner_up", "J")),
    ("R32-9",  "M81", "round_of_32", ("winner", "D"),     ("third_slot", "D")),
    ("R32-10", "M82", "round_of_32", ("winner", "G"),     ("third_slot", "G")),

    # Right Top Branch (→ QF99 → SF102)
    ("R32-4",  "M76", "round_of_32", ("winner", "C"),     ("runner_up", "F")),
    ("R32-6",  "M78", "round_of_32", ("runner_up", "E"),  ("runner_up", "I")),
    ("R32-7",  "M79", "round_of_32", ("winner", "A"),     ("third_slot", "A")),
    ("R32-8",  "M80", "round_of_32", ("winner", "L"),     ("third_slot", "L")),

    # Right Bottom Branch (→ QF100 → SF102)
    ("R32-14", "M86", "round_of_32", ("winner", "J"),     ("runner_up", "H")),
    ("R32-16", "M88", "round_of_32", ("runner_up", "D"),  ("runner_up", "G")),
    ("R32-13", "M85", "round_of_32", ("winner", "B"),     ("third_slot", "B")),
    ("R32-15", "M87", "round_of_32", ("winner", "K"),     ("third_slot", "K")),
]

# Annex C match numbers for later rounds
R16_MATCH_NUMBERS = ["M89", "M90", "M91", "M92", "M93", "M94", "M95", "M96"]
QF_MATCH_NUMBERS = ["M97", "M98", "M99", "M100"]
SF_MATCH_NUMBERS = ["M101", "M102"]
FINAL_MATCH_NUMBER = "M104"
THIRD_PLACE_MATCH_NUMBER = "M103"

KNOCKOUT_STAGE_LAYOUT = [
    ("round_of_32", 16, ROUND_OF_32_TEMPLATE),
    ("round_of_16", 8, [(f"R16-{index}", number, "round_of_16", None, None) for index, number in enumerate(R16_MATCH_NUMBERS, start=1)]),
    ("quarter_finals", 4, [(f"QF-{index}", number, "quarter_finals", None, None) for index, number in enumerate(QF_MATCH_NUMBERS, start=1)]),
    ("semi_finals", 2, [(f"SF-{index}", number, "semi_finals", None, None) for index, number in enumerate(SF_MATCH_NUMBERS, start=1)]),
    ("third_place", 1, [("THIRD-1", THIRD_PLACE_MATCH_NUMBER, "third_place", None, None)]),
    ("final", 1, [("FINAL-1", FINAL_MATCH_NUMBER, "final", None, None)]),
]


def all_knockout_match_templates() -> list[dict[str, str]]:
    """Return placeholder metadata for every knockout match id."""

    templates: list[dict[str, str]] = []
    for stage_name, _, entries in KNOCKOUT_STAGE_LAYOUT:
        for match_id, annex_c, round_name, *_ in entries:
            templates.append(
                {
                    "match_id": match_id,
                    "annex_c": annex_c,
                    "stage": stage_name,
                    "round": round_name,
                }
            )
    return templates


def flatten_bracket_matches(bracket: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the snapshot bracket payload into one list of matches."""

    matches: list[dict[str, Any]] = []
    for stage_name, _, _ in KNOCKOUT_STAGE_LAYOUT:
        stage_payload = bracket.get(stage_name)
        if isinstance(stage_payload, list):
            matches.extend(stage_payload)
        elif isinstance(stage_payload, dict):
            matches.append(stage_payload)
    return matches


def _team_from_reference(
    reference: tuple[str, str],
    group_rankings: dict[str, list[dict[str, Any]]],
    third_place_lookup: dict[str, str],
    third_place_slots: dict[str, str],
) -> tuple[str, str]:
    """Return (team_name, path_label) for a knockout reference."""
    reference_type, group_id = reference
    if reference_type == "winner":
        return group_rankings[group_id][0]["team"], f"1{group_id}"
    if reference_type == "runner_up":
        return group_rankings[group_id][1]["team"], f"2{group_id}"
    if reference_type == "third_slot":
        resolved_group = third_place_slots[group_id]
        return third_place_lookup[resolved_group], f"3{resolved_group}"
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
    for match_id, annex_c, round_name, home_ref, away_ref in ROUND_OF_32_TEMPLATE:
        home_team, home_path = _team_from_reference(home_ref, group_rankings, third_place_lookup, third_place_slots)
        away_team, away_path = _team_from_reference(away_ref, group_rankings, third_place_lookup, third_place_slots)
        matches.append(
            {
                "match_id": match_id,
                "annex_c": annex_c,
                "round": round_name,
                "home_team": home_team,
                "away_team": away_team,
                "home_path": home_path,
                "away_path": away_path,
            }
        )
    return matches, qualified_third


def _resolve_knockout_match(model: EnsembleModel, home_team: str, away_team: str, rng: np.random.Generator, match_id: str) -> dict[str, Any]:
    prediction = model.predict_match(home_team, away_team, match_id=match_id)
    home_goals = int(rng.poisson(prediction["expected_goals"]["home"]))
    away_goals = int(rng.poisson(prediction["expected_goals"]["away"]))
    if home_goals == away_goals:
        winner = pick_penalty_winner(
            home_team, 
            away_team, 
            prediction["features"]["home_penalty_win_rate"], 
            prediction["features"]["away_penalty_win_rate"], 
            prediction["features"]["elo_diff"], 
            rng
        )
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


def _resolve_recorded_knockout_match(
    model: EnsembleModel,
    home_team: str,
    away_team: str,
    match_id: str,
    resolved_entry: dict[str, Any],
) -> dict[str, Any]:
    """Project a resolved knockout match into the bracket payload."""

    prediction = model.predict_match(home_team, away_team, match_id=match_id)
    home_goals = int(resolved_entry["home_goals"])
    away_goals = int(resolved_entry["away_goals"])
    if home_goals == away_goals:
        winner = resolved_entry.get("winner")
        if winner not in {home_team, away_team}:
            raise ValueError(f"Resolved knockout match {match_id} requires a stored winner for drawn scores.")
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
        "result_source": "resolved",
    }


def _project_knockout_match(model: EnsembleModel, home_team: str, away_team: str, match_id: str) -> dict[str, Any]:
    """Resolve a knockout match using the highest advancement probability."""

    prediction = model.predict_match(home_team, away_team, match_id=match_id)
    probs = prediction["outcome_probabilities"]
    penalty_home = penalty_home_probability(
        prediction["features"]["home_penalty_win_rate"],
        prediction["features"]["away_penalty_win_rate"],
        prediction["features"]["elo_diff"],
    )
    home_advance = probs["home_win"] + probs["draw"] * penalty_home
    away_advance = probs["away_win"] + probs["draw"] * (1.0 - penalty_home)
    winner = home_team if home_advance >= away_advance else away_team
    loser = away_team if winner == home_team else home_team

    projected_prediction = {
        **prediction,
        "advancement_probabilities": {
            "home": home_advance,
            "away": away_advance,
        },
    }
    predicted_score = prediction.get("predicted_score", {})
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "winner": winner,
        "loser": loser,
        "score": {
            "home": predicted_score.get("home", "-"),
            "away": predicted_score.get("away", "-"),
        },
        "prediction": projected_prediction,
        "result_source": "projected",
    }


def _play_round(
    model: EnsembleModel,
    pairings: list[dict[str, Any]],
    rng: np.random.Generator,
    resolved_results: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    resolved_results = resolved_results or {}
    results = []
    for pairing in pairings:
        resolved_entry = resolved_results.get(pairing["match_id"])
        if resolved_entry is not None:
            results.append(
                _resolve_recorded_knockout_match(
                    model,
                    pairing["home_team"],
                    pairing["away_team"],
                    pairing["match_id"],
                    resolved_entry,
                )
            )
            continue
        results.append(_resolve_knockout_match(model, pairing["home_team"], pairing["away_team"], rng, pairing["match_id"]))
    return results


def _project_round(
    model: EnsembleModel,
    pairings: list[dict[str, Any]],
    resolved_results: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    resolved_results = resolved_results or {}
    results = []
    for pairing in pairings:
        resolved_entry = resolved_results.get(pairing["match_id"])
        if resolved_entry is not None:
            results.append(
                _resolve_recorded_knockout_match(
                    model,
                    pairing["home_team"],
                    pairing["away_team"],
                    pairing["match_id"],
                    resolved_entry,
                )
            )
            continue
        results.append(_project_knockout_match(model, pairing["home_team"], pairing["away_team"], pairing["match_id"]))
    return results


def _attach_pairing_metadata(pairings: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    for pairing, result in zip(pairings, results):
        result["annex_c"] = pairing.get("annex_c", "")
        result["home_path"] = pairing.get("home_path", "")
        result["away_path"] = pairing.get("away_path", "")


def _next_round_pairings(
    results: list[dict[str, Any]],
    round_prefix: str,
    match_numbers: list[str] | None = None,
) -> list[dict[str, Any]]:
    pairings: list[dict[str, Any]] = []
    for index in range(0, len(results), 2):
        left = results[index]
        right = results[index + 1]
        pair_idx = index // 2
        annex_c = match_numbers[pair_idx] if match_numbers and pair_idx < len(match_numbers) else ""
        pairings.append(
            {
                "match_id": f"{round_prefix}-{pair_idx + 1}",
                "annex_c": annex_c,
                "round": round_prefix,
                "home_team": left["winner"],
                "away_team": right["winner"],
                "home_path": f"W{left.get('annex_c', left['match_id'])}",
                "away_path": f"W{right.get('annex_c', right['match_id'])}",
            }
        )
    return pairings


def simulate_knockout_stage(
    model: EnsembleModel,
    group_rankings: dict[str, list[dict[str, Any]]],
    iterations: int,
    seed: int = 42,
    resolved_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the full 32-team knockout bracket.

    Champion odds come from Monte Carlo simulation. The saved bracket is a
    deterministic projection built by advancing the team with the higher
    knockout advancement probability at each step.
    """

    rng = np.random.default_rng(seed)
    champion_counts: dict[str, int] = defaultdict(int)
    round_of_32_pairings, best_third = build_round_of_32(group_rankings)
    resolved_results = resolved_results or {}

    projected_round_of_32 = _project_round(model, round_of_32_pairings, resolved_results=resolved_results)
    _attach_pairing_metadata(round_of_32_pairings, projected_round_of_32)

    projected_round_of_16_pairings = _next_round_pairings(projected_round_of_32, "R16", R16_MATCH_NUMBERS)
    projected_round_of_16 = _project_round(model, projected_round_of_16_pairings, resolved_results=resolved_results)
    _attach_pairing_metadata(projected_round_of_16_pairings, projected_round_of_16)

    projected_quarter_pairings = _next_round_pairings(projected_round_of_16, "QF", QF_MATCH_NUMBERS)
    projected_quarter_finals = _project_round(model, projected_quarter_pairings, resolved_results=resolved_results)
    _attach_pairing_metadata(projected_quarter_pairings, projected_quarter_finals)

    projected_semi_pairings = _next_round_pairings(projected_quarter_finals, "SF", SF_MATCH_NUMBERS)
    projected_semi_finals = _project_round(model, projected_semi_pairings, resolved_results=resolved_results)
    _attach_pairing_metadata(projected_semi_pairings, projected_semi_finals)

    projected_third_place_pairing = [
        {
            "match_id": "THIRD-1",
            "annex_c": THIRD_PLACE_MATCH_NUMBER,
            "round": "third_place",
            "home_team": projected_semi_finals[0]["loser"],
            "away_team": projected_semi_finals[1]["loser"],
            "home_path": f"L{projected_semi_finals[0].get('annex_c', 'SF1')}",
            "away_path": f"L{projected_semi_finals[1].get('annex_c', 'SF2')}",
        }
    ]
    projected_third_place = _project_round(model, projected_third_place_pairing, resolved_results=resolved_results)[0]
    _attach_pairing_metadata(projected_third_place_pairing, [projected_third_place])

    projected_final_pairings = _next_round_pairings(projected_semi_finals, "FINAL", [FINAL_MATCH_NUMBER])
    projected_final = _project_round(model, projected_final_pairings, resolved_results=resolved_results)[0]
    _attach_pairing_metadata(projected_final_pairings, [projected_final])

    for _ in range(iterations):
        round_of_32 = _play_round(model, round_of_32_pairings, rng, resolved_results=resolved_results)
        _attach_pairing_metadata(round_of_32_pairings, round_of_32)

        round_of_16_pairings = _next_round_pairings(round_of_32, "R16", R16_MATCH_NUMBERS)
        round_of_16 = _play_round(model, round_of_16_pairings, rng, resolved_results=resolved_results)
        _attach_pairing_metadata(round_of_16_pairings, round_of_16)

        quarter_pairings = _next_round_pairings(round_of_16, "QF", QF_MATCH_NUMBERS)
        quarter_finals = _play_round(model, quarter_pairings, rng, resolved_results=resolved_results)
        _attach_pairing_metadata(quarter_pairings, quarter_finals)

        semi_pairings = _next_round_pairings(quarter_finals, "SF", SF_MATCH_NUMBERS)
        semi_finals = _play_round(model, semi_pairings, rng, resolved_results=resolved_results)
        _attach_pairing_metadata(semi_pairings, semi_finals)

        third_place_pairing = [
            {
                "match_id": "THIRD-1",
                "annex_c": THIRD_PLACE_MATCH_NUMBER,
                "round": "third_place",
                "home_team": semi_finals[0]["loser"],
                "away_team": semi_finals[1]["loser"],
                "home_path": f"L{semi_finals[0].get('annex_c', 'SF1')}",
                "away_path": f"L{semi_finals[1].get('annex_c', 'SF2')}",
            }
        ]
        third_place = _play_round(model, third_place_pairing, rng, resolved_results=resolved_results)[0]
        _attach_pairing_metadata(third_place_pairing, [third_place])

        final_pairings = _next_round_pairings(semi_finals, "FINAL", [FINAL_MATCH_NUMBER])
        final_result = _play_round(model, final_pairings, rng, resolved_results=resolved_results)[0]
        _attach_pairing_metadata(final_pairings, [final_result])

        winner = final_result["winner"]
        champion_counts[winner] += 1

    champion_odds = {
        team: round(count / iterations, 4)
        for team, count in sorted(champion_counts.items(), key=lambda item: item[1], reverse=True)
    }

    return {
        "champion_odds": champion_odds,
        "best_third_placed": best_third,
        "bracket": {
            "round_of_32": projected_round_of_32,
            "round_of_16": projected_round_of_16,
            "quarter_finals": projected_quarter_finals,
            "semi_finals": projected_semi_finals,
            "third_place": projected_third_place,
            "final": projected_final,
        },
    }

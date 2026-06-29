"""Feature engineering from official FIFA team statistics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import MATCH_STATE_FILE
from src.data.fifa_official import load_official_team_stats, load_official_tournament_form
from src.utils.constants import GROUP_STAGE_MATCH_COUNT, MATCH_STATE_RESOLVED
from src.utils.helpers import load_json

_RECENT_STATS_COLUMNS = [
    "official_stats_matches_played",
    "official_stats_weight",
    "official_attack_index",
    "official_distribution_index",
    "official_defense_index",
    "official_goalkeeping_index",
    "official_discipline_index",
    "official_movement_index",
    "official_physical_index",
    "official_xg_signal",
    "official_attack_signal",
    "official_defense_signal",
    "official_control_signal",
    "official_recent_form_index",
]


def _first_non_null(series: pd.Series) -> Any:
    non_null = series.dropna()
    if non_null.empty:
        return None
    return non_null.iloc[0]


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _parse_x_multiplier(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace("x", "", regex=False), errors="coerce")


def _centered_rank(series: pd.Series, *, higher_is_better: bool = True) -> pd.Series:
    numeric = _to_numeric(series)
    if numeric.notna().sum() <= 1:
        return pd.Series(0.0, index=series.index, dtype=float)
    ranked = numeric.rank(pct=True, ascending=higher_is_better)
    centered = ranked * 2.0 - 1.0
    return centered.fillna(0.0)


def _average_rank(frame: pd.DataFrame, metrics: list[tuple[str, bool]]) -> pd.Series:
    ranked_columns: list[pd.Series] = []
    for column, higher_is_better in metrics:
        if column not in frame.columns:
            continue
        ranked_columns.append(_centered_rank(frame[column], higher_is_better=higher_is_better))
    if not ranked_columns:
        return pd.Series(0.0, index=frame.index, dtype=float)
    ranked_frame = pd.concat(ranked_columns, axis=1)
    return ranked_frame.mean(axis=1).fillna(0.0)


def official_team_stats_ready() -> bool:
    """Return whether local state shows a completed group stage."""

    state = load_json(MATCH_STATE_FILE, default={}) or {}
    resolved_group_matches = sum(
        1
        for match_id, payload in state.items()
        if str(match_id).startswith("GRP-") and payload.get("state") == MATCH_STATE_RESOLVED
    )
    return resolved_group_matches >= GROUP_STAGE_MATCH_COUNT


def build_official_team_stats_features(
    team_stats: pd.DataFrame,
    tournament_form: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Convert scraped FIFA team-stat tables into compact recent-form features."""

    if team_stats.empty:
        return pd.DataFrame(columns=["team", *_RECENT_STATS_COLUMNS])

    frame = team_stats.copy()
    if "team" not in frame.columns:
        return pd.DataFrame(columns=["team", *_RECENT_STATS_COLUMNS])

    aggregated = (
        frame.sort_values(
            [column for column in ("team", "category", "rank") if column in frame.columns],
            kind="stable",
        )
        .groupby("team", as_index=False)
        .agg(_first_non_null)
        .sort_values("team", kind="stable")
        .reset_index(drop=True)
    )

    if "xg_efficiency" in aggregated.columns:
        aggregated["xg_efficiency_value"] = _parse_x_multiplier(aggregated["xg_efficiency"])

    attack_index = _average_rank(
        aggregated,
        [
            ("goals", True),
            ("xg", True),
            ("attempts_on_target", True),
            ("attempts_at_goal_conv_rate_pct", True),
            ("attempts_inside_the_penalty_area", True),
        ],
    )
    distribution_index = _average_rank(
        aggregated,
        [
            ("passes", True),
            ("passing_accuracy_pct", True),
            ("defensive_linebreaks_attempted", True),
            ("defensive_linebreaks_acc_pct", True),
            ("switches_of_play_acc_pct", True),
        ],
    )
    defense_index = _average_rank(
        aggregated,
        [
            ("goals_conceded", False),
            ("forced_turnovers", True),
            ("ball_recovery_time_s", False),
            ("defensive_pressures_applied", True),
            ("defensive_pressures_directly_applied", True),
        ],
    )
    goalkeeping_index = _average_rank(
        aggregated,
        [
            ("clean_sheets", True),
            ("goals_conceded", False),
            ("goalkeeper_save_percentage_pct", True),
            ("goalkeeper_actions_outside_the_penalty_area", True),
        ],
    )
    discipline_index = _average_rank(
        aggregated,
        [
            ("yellow_cards", False),
            ("red_cards", False),
            ("indirect_red_cards", False),
            ("fouls_against", False),
            ("offsides", False),
        ],
    )
    movement_index = _average_rank(
        aggregated,
        [
            ("offers_to_receive", True),
            ("offers_in_behind", True),
            ("offers_in_between", True),
            ("receptions_in_behind", True),
            ("receptions_between_midfield_and_defensive_line", True),
            ("receptions_under_pressure", True),
        ],
    )
    physical_index = _average_rank(
        aggregated,
        [
            ("average_speed_km_h", True),
            ("high_speed_running", True),
            ("sprints", True),
            ("total_distance_m", True),
        ],
    )
    xg_signal = _average_rank(
        aggregated,
        [
            ("xg", True),
            ("xg_efficiency_value", True),
            ("attempts_on_target", True),
        ],
    )

    stats_features = pd.DataFrame(
        {
            "team": aggregated["team"],
            "official_attack_index": attack_index.round(4),
            "official_distribution_index": distribution_index.round(4),
            "official_defense_index": defense_index.round(4),
            "official_goalkeeping_index": goalkeeping_index.round(4),
            "official_discipline_index": discipline_index.round(4),
            "official_movement_index": movement_index.round(4),
            "official_physical_index": physical_index.round(4),
            "official_xg_signal": xg_signal.round(4),
        }
    )

    if tournament_form is not None and not tournament_form.empty:
        merged_form = stats_features.merge(
            tournament_form[["team", "tournament_matches_played", "tournament_points_pct", "tournament_goal_diff_per_match", "tournament_wins_per_match"]],
            on="team",
            how="left",
        )
        stats_features["official_stats_matches_played"] = (
            pd.to_numeric(merged_form["tournament_matches_played"], errors="coerce").fillna(0.0)
        )
        tournament_form_index = _average_rank(
            merged_form,
            [
                ("tournament_points_pct", True),
                ("tournament_goal_diff_per_match", True),
                ("tournament_wins_per_match", True),
            ],
        )
    else:
        stats_features["official_stats_matches_played"] = 0.0
        tournament_form_index = pd.Series(0.0, index=stats_features.index, dtype=float)

    stats_features["official_stats_weight"] = (stats_features["official_stats_matches_played"] / 10.0).clip(0.0, 0.35)
    stats_features["official_attack_signal"] = (
        0.55 * stats_features["official_attack_index"]
        + 0.2 * stats_features["official_distribution_index"]
        + 0.15 * stats_features["official_movement_index"]
        + 0.1 * stats_features["official_physical_index"]
    ).clip(-1.0, 1.0).round(4)
    stats_features["official_defense_signal"] = (
        0.55 * stats_features["official_defense_index"]
        + 0.25 * stats_features["official_goalkeeping_index"]
        + 0.1 * stats_features["official_discipline_index"]
        + 0.1 * stats_features["official_physical_index"]
    ).clip(-1.0, 1.0).round(4)
    stats_features["official_control_signal"] = (
        0.6 * stats_features["official_distribution_index"]
        + 0.4 * stats_features["official_movement_index"]
    ).clip(-1.0, 1.0).round(4)
    stats_features["official_recent_form_index"] = (
        0.18 * stats_features["official_attack_index"]
        + 0.12 * stats_features["official_distribution_index"]
        + 0.18 * stats_features["official_defense_index"]
        + 0.12 * stats_features["official_goalkeeping_index"]
        + 0.08 * stats_features["official_discipline_index"]
        + 0.1 * stats_features["official_movement_index"]
        + 0.1 * stats_features["official_physical_index"]
        + 0.12 * tournament_form_index
    ).clip(-1.0, 1.0).round(4)
    stats_features["official_xg_signal"] = stats_features["official_xg_signal"].clip(-1.0, 1.0).round(4)
    return stats_features[["team", *_RECENT_STATS_COLUMNS]].sort_values("team").reset_index(drop=True)


def load_official_team_stats_features(require_resolved_state: bool = True) -> pd.DataFrame:
    """Load engineered recent-form features from the official FIFA stats tables."""

    if require_resolved_state and not official_team_stats_ready():
        return pd.DataFrame(columns=["team", *_RECENT_STATS_COLUMNS])
    return build_official_team_stats_features(
        load_official_team_stats(),
        tournament_form=load_official_tournament_form(),
    )

"""Penalty shootout helpers."""

from __future__ import annotations

import numpy as np


def penalty_home_probability(
    home_penalty_rate: float,
    away_penalty_rate: float,
    elo_diff: float,
) -> float:
    """Estimate the home side's shootout win probability."""

    # Default rate is 0.5. We use a Bradley-Terry style approach for the
    # historical rate and blend in a small Elo edge.
    home_rate_bounded = max(0.1, min(0.9, home_penalty_rate))
    away_rate_bounded = max(0.1, min(0.9, away_penalty_rate))

    home_logit = np.log(home_rate_bounded / (1 - home_rate_bounded))
    away_logit = np.log(away_rate_bounded / (1 - away_rate_bounded))

    # 600 Elo difference = 1 logit unit in our scaling.
    elo_logit = elo_diff / 600.0
    combined_logit = (home_logit - away_logit) * 0.7 + elo_logit * 0.3
    return float(1.0 / (1.0 + np.exp(-combined_logit)))


def pick_penalty_winner(
    home_team: str,
    away_team: str,
    home_penalty_rate: float,
    away_penalty_rate: float,
    elo_diff: float,
    rng: np.random.Generator,
) -> str:
    """Resolve a knockout draw using historical penalty performance and Elo difference."""

    home_probability = penalty_home_probability(home_penalty_rate, away_penalty_rate, elo_diff)
    return home_team if rng.random() < home_probability else away_team

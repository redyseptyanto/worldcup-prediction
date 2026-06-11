"""Penalty shootout helpers."""

from __future__ import annotations

import numpy as np


def pick_penalty_winner(home_team: str, away_team: str, elo_diff: float, rng: np.random.Generator) -> str:
    """Resolve a knockout draw with a lightweight Elo-weighted penalty model."""

    home_probability = 1.0 / (1.0 + 10 ** (-elo_diff / 600.0))
    return home_team if rng.random() < home_probability else away_team

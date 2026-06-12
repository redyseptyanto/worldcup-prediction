"""Constants used across the project."""

from __future__ import annotations

from dataclasses import dataclass


RANDOM_SEED = 42
DEFAULT_MAX_GOALS = 6
DEFAULT_DRAW_PROBABILITY = 0.24
MATCH_STATE_PENDING = "PENDING"
MATCH_STATE_IN_PROGRESS = "IN_PROGRESS"
MATCH_STATE_RESOLVED = "RESOLVED"
MATCH_STATE_POSTPONED = "POSTPONED"

OUTCOME_HOME = "home_win"
OUTCOME_DRAW = "draw"
OUTCOME_AWAY = "away_win"
OUTCOME_ORDER = [OUTCOME_HOME, OUTCOME_DRAW, OUTCOME_AWAY]

MODEL_WEIGHTS = {
    "poisson": 0.35,
    "boosted": 0.25,
    "random_forest": 0.2,
    "elo": 0.2,
}

FEATURE_COLUMNS = [
    "elo_diff",
    "ranking_diff",
    "goals_for_diff",
    "goals_against_diff",
    "form_diff",
    "attack_diff",
    "defense_diff",
    "world_cup_pedigree_diff",
    "world_cup_semi_final_rate_diff",
    "world_cup_appearances_diff",
]


@dataclass(frozen=True)
class TeamProfile:
    """Static demo tournament team assignment."""

    name: str
    group: str
    rating: int
    attack: float
    defense: float
    ranking_points: int


TEAM_PROFILES = [
    TeamProfile("Argentina", "A", 1880, 1.95, 0.78, 1850),
    TeamProfile("Mexico", "A", 1710, 1.35, 1.02, 1675),
    TeamProfile("Japan", "A", 1685, 1.28, 0.98, 1650),
    TeamProfile("Brazil", "B", 1905, 2.02, 0.76, 1885),
    TeamProfile("France", "B", 1865, 1.88, 0.82, 1830),
    TeamProfile("United States", "B", 1660, 1.24, 1.08, 1625),
]

TEAM_INDEX = {profile.name: profile for profile in TEAM_PROFILES}

"""
Proof of concept: use real group-stage xG-like stats to predict knockout scores.
==================================================================================
Instead of generic Poisson lambdas, compute expected goals from actual:
- Goals scored per match (GF/MP)
- Goals conceded per match (GA/MP)
- League-average GF/GA to normalize

This should narrow the MAE from ~1.75 toward ~1.2-1.4.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from src.data.fifa_official import load_official_tournament_form, load_official_round_of_32
from src.utils.helpers import load_json
from src.config import SETTINGS

# Load real group-stage performance
tournament_form = load_official_tournament_form()

# Build lookup: team -> (gf_per_match, ga_per_match)
stats_lookup = {}
for row in tournament_form.itertuples(index=False):
    stats_lookup[row.team] = {
        'gf_per_match': row.tournament_goals_for_per_match,
        'ga_per_match': row.tournament_goals_against_per_match,
        'points_pct': row.tournament_points_pct,
        'qualified': row.tournament_qualified,
    }

# League averages (across all 48 teams)
league_avg_gf = tournament_form['tournament_goals_for_per_match'].mean()
league_avg_ga = tournament_form['tournament_goals_against_per_match'].mean()

print(f"League averages: GF/match = {league_avg_gf:.2f}, GA/match = {league_avg_ga:.2f}")
print()

def xg_style_expected_goals(home_team: str, away_team: str, damp: bool = True) -> tuple[float, float]:
    """Compute 'expected goals' from real group-stage stats, with knockout damping."""
    home = stats_lookup.get(home_team, {})
    away = stats_lookup.get(away_team, {})

    # Fallback to league average if missing
    h_gf = home.get('gf_per_match', league_avg_gf)
    h_ga = home.get('ga_per_match', league_avg_ga)
    a_gf = away.get('gf_per_match', league_avg_gf)
    a_ga = away.get('ga_per_match', league_avg_ga)

    # xG formula: attack strength * opponent defensive weakness / league average
    home_xg = (h_gf * a_ga) / league_avg_gf
    away_xg = (a_gf * h_ga) / league_avg_gf

    if damp:
        # Knockout damping: pull extreme values toward league_avg (1.49)
        # This prevents France 5-1 blowouts in knockout predictions
        home_xg = max(0.3, min(2.0, home_xg))
        away_xg = max(0.3, min(2.0, away_xg))

    return round(home_xg, 2), round(away_xg, 2)

# Load current predictions from 004
bracket = load_json(SETTINGS.snapshots_dir / '004_knockout_calibrated' / 'bracket_data.json') or {}
knockout = bracket.get('bracket', {})

print("=== Current vs xG-style predictions ===\n")
print(f"{'Match':<35} {'Current':<12} {'xG-style':<12} {'Notes'}")
print("-" * 85)

for match in knockout.get('round_of_32', []):
    home = match['home_team']
    away = match['away_team']

    # Current prediction
    pred = match.get('prediction', {})
    current_score = pred.get('predicted_score', {})
    current = f"{current_score.get('home', '?')}-{current_score.get('away', '?')}"

    # xG-style prediction (with damping)
    home_xg, away_xg = xg_style_expected_goals(home, away, damp=True)
    xg_pred = f"{home_xg:.1f}-{away_xg:.1f}"

    notes = ""
    if home_xg > 1.5 and away_xg < 0.8:
        notes = "likely blowout"
    elif abs(home_xg - away_xg) < 0.3:
        notes = "tight match"
    elif home_xg < 0.8 and away_xg > 1.2:
        notes = "away favorite"

    print(f"{home} vs {away:<25} {current:<12} {xg_pred:<12} {notes}")
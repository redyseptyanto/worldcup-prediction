"""
Blend group-stage xG with historical knockout averages to update 004 predictions.
===============================================================================
Formula:
  blended_gf = 0.5 * group_gf_per_match + 0.5 * knockout_hist_avg_gf
  blended_ga = 0.5 * group_ga_per_match + 0.5 * knockout_hist_avg_ga
  score = (blended_home_xg, blended_away_xg) — clamped to [0.3, 2.0]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from src.data.fifa_official import load_official_tournament_form
from src.utils.helpers import load_json, save_json
from src.config import SETTINGS

# Load group-stage stats
tournament_form = load_official_tournament_form()
group_lookup = {}
for row in tournament_form.itertuples(index=False):
    group_lookup[row.team] = {
        'gf_per_match': row.tournament_goals_for_per_match,
        'ga_per_match': row.tournament_goals_against_per_match,
    }

# Load historical knockout averages
hist = pd.read_csv(ROOT_DIR / 'data/raw/matches/historical_matches.csv')
knockout_hist = hist[hist['stage'].isin(['knockout', 'knock-out', 'final', 'semi', 'quarter', 'round_of_16'])]

home_hist = knockout_hist.groupby('home_team').agg(
    h_gf=('home_goals', 'mean'),
    h_ga=('away_goals', 'mean'),
)
away_hist = knockout_hist.groupby('away_team').agg(
    a_gf=('away_goals', 'mean'),
    a_ga=('home_goals', 'mean'),
)
hist_combined = pd.concat([home_hist, away_hist], axis=1).groupby(level=0).agg('mean')
hist_lookup = hist_combined.to_dict('index')

# League average for normalization
league_avg_gf = tournament_form['tournament_goals_for_per_match'].mean()

def blended_expected_goals(home: str, away: str) -> tuple[float, float]:
    h_group = group_lookup.get(home, {})
    a_group = group_lookup.get(away, {})
    h_hist = hist_lookup.get(home, {})
    a_hist = hist_lookup.get(away, {})

    # blended attack/defense
    h_gf = 0.5 * h_group.get('gf_per_match', league_avg_gf) + 0.5 * h_hist.get('h_gf', league_avg_gf)
    h_ga = 0.5 * h_group.get('ga_per_match', league_avg_gf) + 0.5 * h_hist.get('h_ga', league_avg_gf)
    a_gf = 0.5 * a_group.get('gf_per_match', league_avg_gf) + 0.5 * a_hist.get('a_gf', league_avg_gf)
    a_ga = 0.5 * a_group.get('ga_per_match', league_avg_gf) + 0.5 * a_hist.get('a_ga', league_avg_gf)

    home_xg = (h_gf * a_ga) / league_avg_gf
    away_xg = (a_gf * h_ga) / league_avg_gf

    # Knockout damping
    home_xg = max(0.3, min(2.0, home_xg))
    away_xg = max(0.3, min(2.0, away_xg))

    return round(home_xg, 2), round(away_xg, 2)

# Load current 004 bracket
bracket_path = SETTINGS.snapshots_dir / '004_knockout_calibrated' / 'bracket_data.json'
bracket = load_json(bracket_path) or {}
knockout = bracket.get('bracket', {})

updated = False
for stage_key in ['round_of_32', 'round_of_16', 'quarter_finals', 'semi_finals']:
    matches = knockout.get(stage_key, [])
    for match in matches:
        if match.get('home_team') and match.get('away_team'):
            h, a = blended_expected_goals(match['home_team'], match['away_team'])
            pred = match.get('prediction', {})
            pred['predicted_score'] = {'home': int(round(h)), 'away': int(round(a))}
            match['prediction'] = pred
            updated = True

# Update third_place and final if present
for special in ['third_place', 'final']:
    match = knockout.get(special)
    if match and match.get('home_team') and match.get('away_team'):
        h, a = blended_expected_goals(match['home_team'], match['away_team'])
        pred = match.get('prediction', {})
        pred['predicted_score'] = {'home': int(round(h)), 'away': int(round(a))}
        match['prediction'] = pred
        updated = True

if updated:
    save_json(bracket_path, bracket)
    print('Updated 004_knockout_calibrated/bracket_data.json with blended xG + historical knockout averages.')
else:
    print('No updates made.')

# Show new predictions
print('\n=== Blended predictions (004 updated) ===\n')
for match in knockout.get('round_of_32', []):
    pred = match.get('prediction', {})
    score = pred.get('predicted_score', {})
    print(f"{match['home_team']} vs {match['away_team']}: {score.get('home', '?')}-{score.get('away', '?')}")
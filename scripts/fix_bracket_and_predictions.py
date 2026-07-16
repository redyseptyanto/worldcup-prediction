"""
Fix bracket data in 004/006 and add knockout predictions to the Predictions tab.
===============================================================================
1. Copy bracket_data.json from 001 to 004 and 006 (they lost it during creation)
2. Generate predictions.json entries for all knockout matches
3. Save updated predictions.json to 004 and 006
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.utils.helpers import load_json, save_json
from src.config import SETTINGS

# Step 1: Copy bracket data from 001 to 004 and 006
source_bracket = load_json(SETTINGS.snapshots_dir / '001_after_group_stage_complete' / 'bracket_data.json') or {}
if not source_bracket.get('bracket'):
    print('ERROR: No bracket data in 001_after_group_stage_complete')
    sys.exit(1)

for target in ['004_knockout_calibrated', '006_blended_knockout_scores']:
    target_path = SETTINGS.snapshots_dir / target / 'bracket_data.json'
    save_json(target_path, source_bracket)
    print(f'Copied bracket_data.json to {target}')

# Step 2: Generate knockout predictions in the same format as group predictions
# Group predictions have columns: match_id, stage, group, home_team, away_team,
# predicted_home_goals, predicted_away_goals, home_win_probability, draw_probability,
# away_win_probability, confidence, confidence_label

knockout_predictions = []
bracket = source_bracket.get('bracket', {})
stage_map = {
    'round_of_32': 'Round of 32',
    'round_of_16': 'Round of 16',
    'quarter_finals': 'Quarter-finals',
    'semi_finals': 'Semi-finals',
    'final': 'Final',
    'third_place': 'Third Place',
}

for stage_key, stage_label in stage_map.items():
    matches = bracket.get(stage_key, [])
    if not isinstance(matches, list):
        matches = [matches] if matches else []
    for m in matches:
        pred = m.get('prediction', {})
        score = pred.get('predicted_score', {})
        probs = pred.get('outcome_probabilities', {})
        confidence = pred.get('confidence', {})
        row = {
            'match_id': m.get('match_id', ''),
            'stage': stage_label,
            'group': '',
            'home_team': m.get('home_team', ''),
            'away_team': m.get('away_team', ''),
            'predicted_home_goals': score.get('home', 0),
            'predicted_away_goals': score.get('away', 0),
            'home_win_probability': probs.get('home_win', 0.0),
            'draw_probability': probs.get('draw', 0.0),
            'away_win_probability': probs.get('away_win', 0.0),
            'confidence': confidence.get('overall', 0.0),
            'confidence_label': confidence.get('label', 'Unknown'),
            'prediction_details': pred,
        }
        knockout_predictions.append(row)

print(f'Generated {len(knockout_predictions)} knockout predictions')

# Step 3: Merge with existing group predictions and save
for target in ['004_knockout_calibrated', '006_blended_knockout_scores']:
    existing = load_json(SETTINGS.snapshots_dir / target / 'predictions.json') or []
    merged = existing + knockout_predictions
    save_json(SETTINGS.snapshots_dir / target / 'predictions.json', merged)
    print(f'Saved {len(merged)} predictions to {target} (was {len(existing)})')

print('\nDone. Refresh Streamlit to see knockout predictions in the Predictions tab.')
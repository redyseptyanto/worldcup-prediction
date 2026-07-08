import sys
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.utils.helpers import load_json
from src.config import SETTINGS

# Check bracket_data.json in 004
bracket = load_json(SETTINGS.snapshots_dir / '004_knockout_calibrated' / 'bracket_data.json') or {}
ko = bracket.get('bracket', {})
for stage_key in ['round_of_32', 'round_of_16', 'quarter_finals', 'semi_finals', 'final', 'third_place']:
    matches = ko.get(stage_key, [])
    if not isinstance(matches, list):
        matches = [matches] if matches else []
    print(f'{stage_key}: {len(matches)} matches')
    for m in matches[:2]:
        print(f'  match_id: {m.get("match_id","")}')
        print(f'  home_team: {m.get("home_team","")}')
        print(f'  away_team: {m.get("away_team","")}')
        pred = m.get('prediction', {})
        print(f'  predicted_score: {pred.get("predicted_score",{})}')
        print(f'  outcome_probs: {pred.get("outcome_probabilities",{})}')
        print(f'  confidence: {pred.get("confidence",{})}')
        print(f'  advancement_probs: {pred.get("advancement_probabilities",{})}')
        print()
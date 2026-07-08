import sys
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.utils.helpers import load_json
from src.config import SETTINGS

# Check predictions.json (what shows in the Predictions tab)
preds = load_json(SETTINGS.snapshots_dir / '004_knockout_calibrated' / 'predictions.json') or []
print('=== predictions.json ===')
print('count:', len(preds))
print('columns:', list(preds[0].keys()))
from collections import Counter
stages = Counter(p.get('stage','?') for p in preds)
print('stages:', dict(stages))
print()

# Check bracket_data.json (what shows in Overview bracket)
bracket = load_json(SETTINGS.snapshots_dir / '004_knockout_calibrated' / 'bracket_data.json') or {}
ko = bracket.get('bracket', {})
print('=== bracket_data.json ===')
for stage_key in ['round_of_32', 'round_of_16', 'quarter_finals', 'semi_finals', 'final', 'third_place']:
    matches = ko.get(stage_key, [])
    if not isinstance(matches, list):
        matches = [matches] if matches else []
    print(f'{stage_key}: {len(matches)} matches')
    for m in matches[:2]:
        pred = m.get('prediction', {})
        score = pred.get('predicted_score', {})
        mid = m.get('match_id', m.get('annex_c', '?'))
        print(f'  {mid}: {m.get("home_team","?")} vs {m.get("away_team","?")} -> {score.get("home","?")}-{score.get("away","?")}')
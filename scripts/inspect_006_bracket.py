import sys
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.utils.helpers import load_json
from src.config import SETTINGS

bracket = load_json(SETTINGS.snapshots_dir / '006_blended_knockout_scores' / 'bracket_data.json') or {}
knockout = bracket.get('bracket', {})
for stage in ['round_of_32', 'round_of_16', 'quarter_finals', 'semi_finals', 'final', 'third_place']:
    matches = knockout.get(stage, [])
    if not isinstance(matches, list):
        matches = [matches] if matches else []
    print(f'{stage}: {len(matches)} matches')
    for m in matches[:2]:
        pred = m.get('prediction', {})
        score = pred.get('predicted_score', {})
        print(f'  {m.get("home_team","?")} vs {m.get("away_team","?")}: {score.get("home","?")}-{score.get("away","?")} | winner={m.get("winner","?")}')
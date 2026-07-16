import sys
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.utils.helpers import load_json
from src.config import SETTINGS
from collections import Counter

for sid in ['004_knockout_calibrated', '006_blended_knockout_scores']:
    preds = load_json(SETTINGS.snapshots_dir / sid / 'predictions.json') or []
    stages = Counter(p.get('stage','?') for p in preds)
    print(f'{sid}: {len(preds)} predictions, stages={dict(stages)}')
    ko = [p for p in preds if p.get('stage') != 'group']
    if ko:
        p = ko[0]
        print(f'  First knockout: {p.get("home_team","")} vs {p.get("away_team","")} -> {p.get("predicted_home_goals","")}-{p.get("predicted_away_goals","")}')
        print(f'  Stage: {p.get("stage","")}')
    print()
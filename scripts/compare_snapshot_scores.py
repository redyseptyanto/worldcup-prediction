import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.utils.helpers import load_json
from src.config import SETTINGS

for sid in ['003_knockout_calibrated', '004_knockout_calibrated', '005_blended_knockout_scores', '006_blended_knockout_scores']:
    bracket = load_json(SETTINGS.snapshots_dir / sid / 'bracket_data.json') or {}
    knockout = bracket.get('bracket', {})
    scores = []
    for m in knockout.get('round_of_32', []):
        pred = m.get('prediction', {})
        score = pred.get('predicted_score', {})
        scores.append(str(score.get('home', '?')) + '-' + str(score.get('away', '?')))
    print(sid + ':')
    print('  ' + ' | '.join(scores[:4]))
    print('  ' + ' | '.join(scores[4:8]))
    print('  ' + ' | '.join(scores[8:12]))
    print('  ' + ' | '.join(scores[12:16]))
    print()
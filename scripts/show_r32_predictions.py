import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.utils.helpers import load_json
from src.config import SETTINGS

bracket = load_json(SETTINGS.snapshots_dir / '004_knockout_calibrated' / 'bracket_data.json') or {}
knockout = bracket.get('bracket', {})

print('=== Round of 32 Predictions (004_knockout_calibrated) ===\n')
for match in knockout.get('round_of_32', []):
    pred = match.get('prediction', {})
    probs = pred.get('outcome_probabilities', {})
    score = pred.get('predicted_score', {})
    home = match['home_team']
    away = match['away_team']
    print(f"{home} vs {away}")
    print(f"  Predicted score: {score.get('home', '?')}-{score.get('away', '?')}")
    print(f"  Probs: home={probs.get('home_win', 0):.1%} draw={probs.get('draw', 0):.1%} away={probs.get('away_win', 0):.1%}")
    print()
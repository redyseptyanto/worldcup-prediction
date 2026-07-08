"""
1. Remove duplicate predictions from 004 and 006
2. Re-copy group predictions from 001
3. Re-generate clean knockout predictions
"""

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.utils.helpers import load_json, save_json
from src.config import SETTINGS

# Get unique predictions by match_id (keep first occurrence)
for sid in ['004_knockout_calibrated', '006_blended_knockout_scores']:
    preds = load_json(SETTINGS.snapshots_dir / sid / 'predictions.json') or []
    seen = set()
    unique = []
    for p in preds:
        mid = p.get('match_id', '')
        if mid not in seen:
            seen.add(mid)
            unique.append(p)
    print(f'{sid}: deduped {len(preds)} -> {len(unique)}')
    save_json(SETTINGS.snapshots_dir / sid / 'predictions.json', unique)

# Now re-run the copy
exec(open(ROOT / 'scripts' / 'copy_group_predictions.py').read())
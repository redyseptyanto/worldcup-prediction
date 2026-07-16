"""
Copy group predictions from 001 to all newer snapshots that are missing them.
===============================================================================
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.utils.helpers import load_json, save_json
from src.config import SETTINGS

source = load_json(SETTINGS.snapshots_dir / '001_after_group_stage_complete' / 'predictions.json') or []
if not source:
    print('ERROR: No predictions in 001_after_group_stage_complete')
    sys.exit(1)

group_preds = [p for p in source if p.get('stage') == 'group']
print(f'Found {len(group_preds)} group predictions in 001')

for sid in ['002_after_official_team_stats', '004_knockout_calibrated', '006_blended_knockout_scores']:
    existing = load_json(SETTINGS.snapshots_dir / sid / 'predictions.json') or []
    # Keep any knockout preds that might already be there
    knockout_existing = [p for p in existing if p.get('stage') != 'group']
    merged = group_preds + knockout_existing
    save_json(SETTINGS.snapshots_dir / sid / 'predictions.json', merged)
    print(f'Saved {len(merged)} predictions to {sid} (group={len(group_preds)}, knockout={len(knockout_existing)})')

print('Done. Refresh Streamlit.')
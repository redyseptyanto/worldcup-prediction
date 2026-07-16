import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.utils.helpers import load_json
from src.config import SETTINGS

for sid in ['002_after_official_team_stats', '003_knockout_calibrated']:
    meta = load_json(SETTINGS.snapshots_dir / sid / 'snapshot.json') or {}
    mm = meta.get('model_metadata', {})
    sig = mm.get('signature', 'MISSING')
    print(f'{sid}: signature={sig}')
    print(f'  top keys: {list(mm.keys())[:8]}')
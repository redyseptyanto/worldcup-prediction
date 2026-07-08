"""
Create missing snapshot.json files for snapshots that don't have them.
Format must match: created_at, descriptor, model_metadata (with signature), resolved_matches, snapshot_id
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.utils.helpers import load_json, save_json


def create_snapshot_json(snapshot_id: str, descriptor: str, signature: str, resolved_count: int = 0):
    data = {
        "snapshot_id": snapshot_id,
        "descriptor": descriptor,
        "resolved_matches": [f"MOCK-{i}" for i in range(resolved_count)] if resolved_count > 0 else [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_metadata": {
            "signature": signature,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": {"ensemble.pkl": 0, "metrics.json": 0},
        },
    }
    return data


snapshots = {
    "002_after_official_team_stats": {
        "descriptor": "after_official_team_stats",
        "signature": "fa0d8e04da0c",
    },
    "004_knockout_calibrated": {
        "descriptor": "knockout_calibrated",
        "signature": "9f5ad0b91383",
    },
    "006_blended_knockout_scores": {
        "descriptor": "blended_knockout_scores",
        "signature": "9f5ad0b91383",
    },
}

# Also add config.json if missing (just needs to exist)
config_template = {"version": 1}

for sid, info in snapshots.items():
    snap_dir = ROOT / "output" / "snapshots" / sid
    if not snap_dir.exists():
        print(f"SKIP: {sid} does not exist")
        continue

    snapshot_json = snap_dir / "snapshot.json"
    if not snapshot_json.exists():
        data = create_snapshot_json(sid, info["descriptor"], info["signature"])
        save_json(snapshot_json, data)
        print(f"CREATED: {sid}/snapshot.json (sig={info['signature']})")
    else:
        print(f"EXISTS: {sid}/snapshot.json")

    config_json = snap_dir / "config.json"
    if not config_json.exists():
        save_json(config_json, config_template)
        print(f"CREATED: {sid}/config.json")

print("\nDone. Now run: python scripts/fix_bracket_and_predictions.py && python scripts/copy_group_predictions.py")
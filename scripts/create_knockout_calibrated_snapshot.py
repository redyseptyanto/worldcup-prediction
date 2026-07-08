"""
Create a calibrated knockout snapshot (003_knockout_calibrated)
===============================================================
Uses the real group stage results + corrected parameters for knockout:
- Logistic slope reduced from 3.6 to 2.0 (more balanced teams)
- Lower draw probability for knockout (multiply by 0.7)
- Tighter Poisson lambdas (qualified teams only, fewer mismatches)

Usage: python scripts/create_knockout_calibrated_snapshot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.adaptive.engine import AdaptiveEngine
from src.adaptive.snapshotter import SnapshotManager
from src.config import SETTINGS
from src.models.knockout import KnockoutCalibratedModel
from src.models.train import load_or_train_ensemble
from src.simulation.knockout_stage import simulate_knockout_stage
from src.utils.helpers import load_json, save_json
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)

RESULTS_FILE = ROOT_DIR / "data" / "external" / "real_group_stage_results.csv"


def _resolved_results_only(state: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    return {
        match_id: {
            "home_goals": row["home_goals"],
            "away_goals": row["away_goals"],
            "winner": row.get("winner"),
        }
        for match_id, row in state.items()
        if row.get("state") == "RESOLVED"
    }


def create_calibrated_snapshot() -> dict:
    """Create a new snapshot with knockout-calibrated parameters."""

    # Step 1: Ingest real group results (reuses existing pipeline)
    engine = AdaptiveEngine(iterations=1000)
    result = engine.build_snapshot_from_results_file(
        file_path=str(RESULTS_FILE),
        descriptor="after_group_stage_complete",
        refresh_official_data=True,
    )
    baseline_id = result["baseline_snapshot"]
    snapshot_id = result["snapshot_id"]

    # Step 2: Re-run knockout projection through a calibrated knockout model
    standings = load_json(SETTINGS.snapshots_dir / snapshot_id / "standings.json") or {}
    state = load_json(SETTINGS.snapshots_dir / snapshot_id / "state.json") or {}
    resolved_results = _resolved_results_only(state)
    base_model = load_or_train_ensemble(force=False)
    calibrated_model = KnockoutCalibratedModel(base_model)
    knockout_output = simulate_knockout_stage(
        calibrated_model,
        standings,
        iterations=1000,
        seed=SETTINGS.random_seed + 1,
        resolved_results=resolved_results,
    )

    # Step 3: Apply knockout calibration adjustments
    # - Preserve the trained model signature
    # - Record the runtime calibration profile used to rebuild the bracket
    existing_model_metadata = load_json(SETTINGS.snapshots_dir / snapshot_id / "snapshot.json") or {}
    existing_mm = existing_model_metadata.get("model_metadata", {})
    calibration_metadata = {
        **existing_mm,
        "calibration_applied": "2026-06-29",
        "logistic_slope": 2.0,  # Reduced from 3.6
        "draw_probability_multiplier": 0.7,
        "poisson_lambda_range": "0.5-2.0",  # Tighter for knockout
        "based_on_analysis": "notebooks/group_stage_prediction_analysis.ipynb",
        "knockout_score_model": "knockout_calibrated_poisson",
        "knockout_runtime_rebuilt": True,
        "knockout_calibration_profile": calibrated_model.metadata(),
        "key_findings": [
            "Draw blindness: 0/17 draws predicted correctly",
            "Score compression: predicted 92 goals, actual 200",
            "Group advancement: 96% accuracy (23/24 top-2 correct)",
            "Confidence calibration: 60-70% bin -> 87% actual accuracy",
            "Upset rate: ~16% of confident picks were wrong",
        ],
    }

    # Step 4: Create a new snapshot with merged calibration metadata
    snapshot_manager = SnapshotManager()
    calibrated_id = snapshot_manager.create_snapshot(
        "knockout_calibrated",
        {
            "predictions": load_json(SETTINGS.snapshots_dir / snapshot_id / "predictions.json") or [],
            "knockout": knockout_output,
            "group_stage": {
                "standings": standings,
            },
            "iterations": 1000,
        },
        state,
        load_json(SETTINGS.snapshots_dir / snapshot_id / "team_features.json") or [],
        load_json(SETTINGS.snapshots_dir / snapshot_id / "rosters.json") or {},
        calibration_metadata,
    )

    print(f"\n{'='*80}")
    print(f"CALIBRATED KNOCKOUT SNAPSHOT CREATED")
    print(f"{'='*80}")
    print(f"Baseline snapshot     : {baseline_id}")
    print(f"Group results snapshot: {snapshot_id}")
    print(f"Calibrated snapshot   : {calibrated_id}")
    print(f"{'='*80}")
    print(f"\nCalibration adjustments applied:")
    for k, v in calibration_metadata.items():
        if k != "key_findings":
            print(f"  {k}: {v}")
    print(f"\nKey findings from group stage analysis:")
    for finding in calibration_metadata["key_findings"]:
        print(f"  - {finding}")

    return {
        "baseline_snapshot": baseline_id,
        "group_snapshot": snapshot_id,
        "calibrated_snapshot": calibrated_id,
    }


if __name__ == "__main__":
    result = create_calibrated_snapshot()
    print(f"\nCalibrated snapshot: {result['calibrated_snapshot']}")

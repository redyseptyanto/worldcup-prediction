"""
Create snapshot 005 with blended xG + historical knockout score predictions.
=============================================================================
Pipeline:
1. Ingest real group stage results (same as 004)
2. Apply knockout calibrations (logistic slope 2.0, etc.)
3. Override predicted scores with blended xG + historical knockout averages
4. Save as new snapshot 005
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from src.adaptive.snapshotter import SnapshotManager
from src.config import SETTINGS
from src.models.knockout import KnockoutBlendedModel
from src.models.train import load_or_train_ensemble
from src.simulation.knockout_stage import simulate_knockout_stage
from src.utils.helpers import load_json
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


def _latest_snapshot_id(descriptor: str) -> str:
    snapshot_manager = SnapshotManager()
    matches = [
        detail["snapshot_id"]
        for detail in snapshot_manager.list_snapshot_details()
        if detail.get("descriptor") == descriptor
    ]
    if not matches:
        raise FileNotFoundError(f"No snapshot found for descriptor '{descriptor}'.")
    return matches[-1]


def create_blended_snapshot() -> dict:
    # Step 1: Use the latest calibrated knockout snapshot as base
    base_snapshot_id = _latest_snapshot_id('knockout_calibrated')

    # Step 2: Load data for blending and rebuild the knockout bracket through the blended adapter
    from src.data.fifa_official import load_official_tournament_form
    tournament_form = load_official_tournament_form()
    hist = pd.read_csv(ROOT_DIR / 'data/raw/matches/historical_matches.csv')
    standings = load_json(SETTINGS.snapshots_dir / base_snapshot_id / 'standings.json') or {}
    state = load_json(SETTINGS.snapshots_dir / base_snapshot_id / 'state.json') or {}
    resolved_results = _resolved_results_only(state)
    base_model = load_or_train_ensemble(force=False)
    blended_model = KnockoutBlendedModel(
        base_model,
        tournament_form=tournament_form,
        historical_matches=hist,
    )
    knockout_output = simulate_knockout_stage(
        blended_model,
        standings,
        iterations=1000,
        seed=SETTINGS.random_seed + 1,
        resolved_results=resolved_results,
    )

    # Step 3: Create new snapshot 005
    snapshot_manager = SnapshotManager()
    model_metadata = load_json(SETTINGS.snapshots_dir / base_snapshot_id / 'snapshot.json') or {}
    mm = model_metadata.get('model_metadata', {})

    blended_metadata = {
        **mm,
        'calibration_applied': '2026-06-29',
        'logistic_slope': 2.0,
        'draw_probability_multiplier': 0.7,
        'poisson_lambda_range': '0.5-2.0',
        'score_model': 'knockout_calibrated_form_history_blend',
        'blend_weights': {
            'model_expected_goals': blended_model.blend_profile.model_weight,
            'tournament_form': blended_model.blend_profile.tournament_weight,
            'historical_rates': blended_model.blend_profile.history_weight,
            'score_probability_weight': blended_model.blend_profile.score_probability_weight,
        },
        'historical_scope': blended_model.history_scope,
        'knockout_runtime_rebuilt': True,
        'knockout_blend_profile': blended_model.metadata(),
        'based_on_analysis': 'notebooks/group_stage_prediction_analysis.ipynb',
        'key_findings': [
            'Draw blindness: 0/17 draws predicted correctly',
            'Score compression: predicted 92 goals, actual 200',
            'Group advancement: 96% accuracy (23/24 top-2 correct)',
            'Confidence calibration: 60-70% bin -> 87% actual accuracy',
            'Upset rate: ~16% of confident picks were wrong',
            'Score model: calibrated model xG blended with tournament form and historical rates',
        ],
    }

    new_id = snapshot_manager.create_snapshot(
        'blended_knockout_scores',
        {
            'predictions': load_json(SETTINGS.snapshots_dir / base_snapshot_id / 'predictions.json') or [],
            'knockout': knockout_output,
            'group_stage': {
                'standings': standings,
            },
            'iterations': 1000,
        },
        state,
        load_json(SETTINGS.snapshots_dir / base_snapshot_id / 'team_features.json') or [],
        load_json(SETTINGS.snapshots_dir / base_snapshot_id / 'rosters.json') or {},
        blended_metadata,
    )

    print(f"\n{'='*80}")
    print(f"BLENDED KNOCKOUT SNAPSHOT CREATED")
    print(f"{'='*80}")
    print(f"Base snapshot        : {base_snapshot_id}")
    print(f"Blended snapshot     : {new_id}")
    print(f"{'='*80}")
    return {'base_snapshot': base_snapshot_id, 'blended_snapshot': new_id}


if __name__ == '__main__':
    res = create_blended_snapshot()
    print(f"\nUse snapshot '{res['blended_snapshot']}' in Streamlit.")

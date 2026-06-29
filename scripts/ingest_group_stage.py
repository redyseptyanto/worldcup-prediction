"""Ingest all 2026 FIFA World Cup group stage results and recalibrate knockout predictions.

This script:
1. Reads real group stage results from data/external/real_group_stage_results.csv
2. Ingests each result into the adaptive state machine
3. Recalibrates the ensemble with the actual results
4. Re-simulates the tournament forward only on future rounds
5. Creates a new post-group-stage snapshot
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.adaptive.engine import AdaptiveEngine
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)

RESULTS_FILE = ROOT_DIR / "data" / "external" / "real_group_stage_results.csv"


def ingest_group_stage(results_file: Path = RESULTS_FILE, iterations: int = 1000) -> dict:
    """Ingest all group stage results and produce a recalibrated snapshot."""

    engine = AdaptiveEngine(iterations=iterations)
    result = engine.build_snapshot_from_results_file(
        file_path=str(results_file),
        descriptor="after_group_stage_complete",
        refresh_official_data=True,
    )
    LOGGER.info("Group stage ingestion complete. %d matches ingested.", result["matches_ingested"])

    # Print summary
    print(f"\n{'='*80}")
    print(f"GROUP STAGE INGESTION COMPLETE")
    print(f"{'='*80}")
    print(f"Total matches ingested : {result['matches_ingested']}")
    print(f"Last snapshot          : {result['snapshot_id']}")
    print(f"Iterations used        : {iterations}")
    print(f"{'='*80}\n")
    return {
        "baseline_snapshot": result["baseline_snapshot"],
        "final_snapshot": result["snapshot_id"],
        "matches_ingested": result["matches_ingested"],
        "responses": result["ingested"],
    }


if __name__ == "__main__":
    result = ingest_group_stage()
    print(f"\nFinal snapshot: {result['final_snapshot']}")

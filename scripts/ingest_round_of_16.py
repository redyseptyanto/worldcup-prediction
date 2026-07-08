"""Ingest official Round-of-16 results and recalibrate knockout predictions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.adaptive.engine import AdaptiveEngine
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)


def ingest_round_of_16(iterations: int = 1000) -> dict:
    """Build the official after-Round-of-16 snapshot."""

    engine = AdaptiveEngine(iterations=iterations)
    result = engine.build_snapshot_after_round_of_16(
        descriptor="after_round_of_16_complete",
        refresh_official_data=True,
    )

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Baseline snapshot           : {result['baseline_snapshot']}")
    print(f"  Final snapshot ID           : {result['snapshot_id']}")
    print(f"  Group matches ingested      : {result['group_matches_ingested']}")
    print(f"  Round of 32 matches ingested: {result['round_of_32_matches_ingested']}")
    print(f"  Round of 16 matches ingested: {result['round_of_16_matches_ingested']}")
    print(f"  Iterations used             : {iterations}")
    print(f"{'=' * 80}\n")

    return {
        "baseline_snapshot": result["baseline_snapshot"],
        "final_snapshot": result["snapshot_id"],
        "group_matches_ingested": result["group_matches_ingested"],
        "round_of_32_matches_ingested": result["round_of_32_matches_ingested"],
        "round_of_16_matches_ingested": result["round_of_16_matches_ingested"],
    }


if __name__ == "__main__":
    result = ingest_round_of_16()
    print(f"\nDone. Final snapshot: {result['final_snapshot']}")

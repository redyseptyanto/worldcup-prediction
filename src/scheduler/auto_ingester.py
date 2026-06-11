"""Auto-ingest available results."""

from __future__ import annotations

from src.adaptive.engine import AdaptiveEngine
from src.scheduler.fetch_results import fetch_available_results


def run_auto_ingest() -> dict[str, object]:
    """Fetch and ingest any available offline sample results."""

    engine = AdaptiveEngine()
    available = fetch_available_results()
    if not available:
        return {"count": 0, "snapshots": []}
    return engine.ingest_batch(available)

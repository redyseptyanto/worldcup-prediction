from pathlib import Path

from src.adaptive.engine import AdaptiveEngine


def test_adaptive_ingest_creates_snapshot() -> None:
    engine = AdaptiveEngine(iterations=50)
    baseline = engine.create_baseline_snapshot()
    response = engine.ingest_result("GRP-A-M1", 2, 1)

    assert baseline.startswith("000_")
    assert response["snapshot_id"] != baseline
    assert "R32-1" in response["affected_matches"]
    assert "SF-1" in response["affected_matches"]


def test_baseline_snapshot_populates_knockout_state() -> None:
    engine = AdaptiveEngine(iterations=25)
    engine.create_baseline_snapshot()

    round_of_32_match = engine.state_machine.get("R32-1")

    assert round_of_32_match is not None
    assert round_of_32_match["home_team"] != "TBD"
    assert round_of_32_match["away_team"] != "TBD"


def test_build_snapshot_from_results_file_preserves_baseline_state(tmp_path: Path) -> None:
    engine = AdaptiveEngine(iterations=25)
    baseline = engine.create_baseline_snapshot()
    results_file = tmp_path / "results.csv"
    results_file.write_text("match_id,home_goals,away_goals\nGRP-A-M1,2,1\n", encoding="utf-8")

    response = engine.build_snapshot_from_results_file(
        str(results_file),
        descriptor="after_test_batch",
        refresh_official_data=False,
    )

    refreshed_engine = AdaptiveEngine(iterations=25)

    assert baseline == "000_baseline"
    assert response["baseline_snapshot"] == baseline
    assert response["snapshot_id"] == "001_after_test_batch"
    assert response["matches_ingested"] == 1
    assert refreshed_engine.state_machine.resolved_results() == {}

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

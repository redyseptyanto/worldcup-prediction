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


def test_latest_snapshot_with_descriptor_prefers_newest_entry() -> None:
    engine = AdaptiveEngine(iterations=25)
    engine._snapshot_details = lambda: [  # type: ignore[method-assign]
        {"snapshot_id": "001_after_round_of_32_complete", "descriptor": "after_round_of_32_complete"},
        {"snapshot_id": "002_other", "descriptor": "other"},
        {"snapshot_id": "003_after_round_of_32_complete", "descriptor": "after_round_of_32_complete"},
    ]

    latest = engine._latest_snapshot_with_descriptor("after_round_of_32_complete")  # noqa: SLF001

    assert latest is not None
    assert latest["snapshot_id"] == "003_after_round_of_32_complete"


def test_resolve_knockout_match_id_falls_back_to_reversed_teams() -> None:
    engine = AdaptiveEngine(iterations=25)
    engine.state_machine._state = {  # type: ignore[attr-defined]
        "R16-5": {"home_team": "Brazil", "away_team": "Norway"},
    }

    match_id, reversed_teams = engine._resolve_knockout_match_id("R16-", "Norway", "Brazil")  # noqa: SLF001

    assert match_id == "R16-5"
    assert reversed_teams is True

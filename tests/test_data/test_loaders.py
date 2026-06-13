from src.data.collector import collect_all
from src.data.loaders import initialize_state_store, load_fixtures, load_historical_matches, load_rankings


def test_loader_pipeline_creates_tournament_inputs() -> None:
    collect_all()
    matches = load_historical_matches()
    rankings = load_rankings()
    fixtures = load_fixtures()
    state = initialize_state_store()

    assert not matches.empty
    assert len(rankings) >= 48
    assert len(fixtures) == 72
    assert len(state) == 104
    assert state["R32-1"]["home_team"] == "TBD"
    assert state["FINAL-1"]["stage"] == "final"
    tournament_teams = set(rankings.loc[rankings["group"].fillna("") != "", "team"])
    assert {"Brazil", "Canada", "England", "Mexico", "South Korea", "United States"}.issubset(tournament_teams)

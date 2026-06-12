from src.data.loaders import load_historical_matches
from src.features.world_cup_pedigree import build_world_cup_pedigree_history, summarize_world_cup_pedigree


def test_world_cup_pedigree_prefers_deeper_recent_runs() -> None:
    history = build_world_cup_pedigree_history(load_historical_matches())
    summary = summarize_world_cup_pedigree(history)

    assert summary["Argentina"]["world_cup_pedigree"] > summary["Mexico"]["world_cup_pedigree"]
    assert summary["France"]["world_cup_semi_final_rate"] >= 0.5
    assert summary["France"]["world_cup_appearances"] >= 2.0

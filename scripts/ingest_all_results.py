"""Ingest all real results (group stage + Round of 32) and recalibrate predictions.

Direct approach: 
1. Initialize state machine with fixtures
2. Directly set all group stage results in state file
3. Directly set all R32 results in state file (with correct teams from bracket)
4. Retrain model once
5. Re-simulate tournament (now includes knockout predictions)
6. Create snapshot
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import json
import pandas as pd
from src.data.fifa_official import refresh_official_fifa_data, canonical_team_name
from src.data.loaders import initialize_state_store
from src.models.train import train_models, current_model_metadata
from src.simulation.tournament import TournamentSimulator
from src.utils.helpers import load_json, save_json
from src.config import ROSTERS_FILE, TEAM_FEATURES_FILE, MATCH_STATE_FILE
from src.utils.logger import get_logger
from src.utils.constants import MATCH_STATE_RESOLVED

LOGGER = get_logger(__name__)

GROUP_RESULTS_FILE = ROOT_DIR / "data" / "external" / "real_group_stage_results.csv"
R32_RESULTS_FILE = ROOT_DIR / "data" / "external" / "real_round_of_32_results.csv"

ANNEX_TO_R32_ID = {
    "M73": "R32-1", "M74": "R32-2", "M75": "R32-3", "M76": "R32-4",
    "M77": "R32-5", "M78": "R32-6", "M79": "R32-7", "M80": "R32-8",
    "M81": "R32-9", "M82": "R32-10", "M83": "R32-11", "M84": "R32-12",
    "M85": "R32-13", "M86": "R32-14", "M87": "R32-15", "M88": "R32-16",
}


def load_official_r32_results() -> list[dict]:
    """Load actual R32 results from the FIFA official bracket JSON."""
    bracket_file = ROOT_DIR / "data" / "external" / "fifa_official_bracket.json"
    with open(bracket_file) as f:
        data = json.load(f)
    
    results = []
    for stage in data.get("KnockoutStages", []):
        name = (stage.get("Name") or [{}])[0].get("Description", "")
        if "Round of 32" not in name:
            continue
        for match in stage.get("Matches", []):
            status = match.get("MatchStatus")
            if status != 0:
                continue
            home = match.get("HomeTeam") or {}
            away = match.get("AwayTeam") or {}
            home_name = canonical_team_name(
                ((home.get("TeamName") or [{}])[0]).get("Description", "")
            )
            away_name = canonical_team_name(
                ((away.get("TeamName") or [{}])[0]).get("Description", "")
            )
            home_score = home.get("Score")
            away_score = away.get("Score")
            match_num = match.get("MatchNumber")
            annex = f"M{match_num}"
            r32_id = ANNEX_TO_R32_ID.get(annex)
            if r32_id is None:
                continue
            winner = None
            if home_score is not None and away_score is not None:
                if home_score > away_score:
                    winner = home_name
                elif away_score > home_score:
                    winner = away_name
                elif home_score == away_score:
                    winner_id = match.get("Winner")
                    if winner_id == home.get("IdTeam"):
                        winner = home_name
                    elif winner_id == away.get("IdTeam"):
                        winner = away_name
            
            results.append({
                "r32_id": r32_id,
                "home_team": home_name,
                "away_team": away_name,
                "home_goals": home_score,
                "away_goals": away_score,
                "winner": winner,
            })
    
    return results


def ingest_all_results(iterations: int = 1000) -> dict:
    """Ingest all group stage + R32 results and produce recalibrated snapshots."""

    print(f"\n{'='*80}")
    print("STEP 1: Refreshing official FIFA data...")
    print(f"{'='*80}")
    refresh_result = refresh_official_fifa_data()
    print(f"  Standings: {refresh_result.get('standings_csv')}")

    print(f"\n{'='*80}")
    print("STEP 2: Loading official R32 results from bracket data...")
    print(f"{'='*80}")
    
    official_results = load_official_r32_results()
    print(f"  Found {len(official_results)} completed R32 matches")
    
    r32_csv = pd.read_csv(R32_RESULTS_FILE)
    winner_map = {}
    for row in r32_csv.itertuples(index=False):
        winner_map[str(row.match_id)] = str(row.winner)

    print(f"\n{'='*80}")
    print("STEP 3: Initializing state machine and setting all results...")
    print(f"{'='*80}")
    
    # Clean state and re-initialize
    if MATCH_STATE_FILE.exists():
        MATCH_STATE_FILE.unlink()
    state = initialize_state_store()
    print(f"  Initialized state with {len(state)} matches")
    
    # Read group stage results
    group_df = pd.read_csv(GROUP_RESULTS_FILE, comment="#")
    
    # Set group stage results
    group_count = 0
    for row in group_df.itertuples(index=False):
        match_id = str(row.match_id)
        if match_id in state:
            state[match_id]["state"] = MATCH_STATE_RESOLVED
            state[match_id]["home_goals"] = int(row.home_goals)
            state[match_id]["away_goals"] = int(row.away_goals)
            if int(row.home_goals) > int(row.away_goals):
                state[match_id]["winner"] = state[match_id]["home_team"]
            elif int(row.away_goals) > int(row.home_goals):
                state[match_id]["winner"] = state[match_id]["away_team"]
            else:
                state[match_id]["winner"] = None
            group_count += 1
    print(f"  Set {group_count} group stage results")
    
    # Set R32 results with correct teams
    r32_count = 0
    for r in official_results:
        r32_id = r["r32_id"]
        if r32_id in state:
            current = state[r32_id]
            current["home_team"] = r["home_team"]
            current["away_team"] = r["away_team"]
            winner = r["winner"]
            if winner is None and r["home_goals"] == r["away_goals"]:
                winner = winner_map.get(r32_id)
            current["state"] = MATCH_STATE_RESOLVED
            current["home_goals"] = r["home_goals"]
            current["away_goals"] = r["away_goals"]
            current["winner"] = winner
            r32_count += 1
            print(f"  ✓ {r32_id}: {r['home_team']} {r['home_goals']}-{r['away_goals']} {r['away_team']} (winner: {winner})")
    
    # Save state
    save_json(MATCH_STATE_FILE, state)
    print(f"\n  Saved {group_count} group + {r32_count} R32 results to state file")

    print(f"\n{'='*80}")
    print("STEP 4: Retraining ensemble model with all results...")
    print(f"{'='*80}")
    train_models(force=True)
    print("  Model retrained successfully")

    print(f"\n{'='*80}")
    print("STEP 5: Re-simulating tournament...")
    print(f"{'='*80}")

    from src.adaptive.state_machine import MatchStateMachine
    state_machine = MatchStateMachine()
    resolved = state_machine.resolved_results()
    print(f"  Resolved matches: {len(resolved)}")

    simulator = TournamentSimulator(iterations=iterations)
    output = simulator.run(resolved_results=resolved)
    state_machine.sync_knockout_matches(output)
    print("  Tournament re-simulated successfully")
    
    # Check predictions count
    preds = output.get("predictions", [])
    pred_stages = {}
    for p in preds:
        stage = p.get("stage", "unknown")
        pred_stages[stage] = pred_stages.get(stage, 0) + 1
    print(f"  Predictions by stage: {pred_stages}")

    print(f"\n{'='*80}")
    print("STEP 6: Creating after_round_of_32_complete snapshot...")
    print(f"{'='*80}")

    from src.adaptive.snapshotter import SnapshotManager
    snapshot_manager = SnapshotManager()
    
    team_features = load_json(TEAM_FEATURES_FILE, default=[])
    rosters = load_json(ROSTERS_FILE, default={})
    model_metadata = current_model_metadata()

    snapshot_id = snapshot_manager.create_snapshot(
        "after_round_of_32_complete",
        output,
        state_machine._state,
        team_features,
        rosters,
        model_metadata,
    )
    print(f"  Snapshot ID: {snapshot_id}")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"  Final snapshot      : {snapshot_id}")
    print(f"  Group matches       : {group_count}")
    print(f"  R32 matches         : {r32_count}")
    print(f"  Total resolved      : {len(resolved)}")
    print(f"  Total predictions   : {len(preds)}")
    print(f"{'='*80}\n")

    # Print R16 teams
    print("Round of 16 teams:")
    r16 = {k: v for k, v in state_machine._state.items() if k.startswith("R16-")}
    for k in sorted(r16.keys()):
        v = r16[k]
        st = " (RESOLVED)" if v["state"] == MATCH_STATE_RESOLVED else ""
        print(f"  {k}: {v['home_team']} vs {v['away_team']}{st}")

    print(f"\nChampion odds (top 10):")
    for team, odds in sorted(output.get("knockout", {}).get("champion_odds", {}).items(), key=lambda x: -x[1])[:10]:
        print(f"  {team}: {odds*100:.1f}%")

    return {
        "snapshot": snapshot_id,
        "group_matches": group_count,
        "r32_matches": r32_count,
        "predictions": len(preds),
    }


if __name__ == "__main__":
    result = ingest_all_results()
    print(f"\nDone. Snapshot: {result['snapshot']}, Predictions: {result['predictions']}")
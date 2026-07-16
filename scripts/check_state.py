"""Check current match state for R32 matches."""
import json
from pathlib import Path

state_file = Path("output/state/matches.json")
if state_file.exists():
    state = json.loads(state_file.read_text())
    r32_matches = {k: v for k, v in state.items() if k.startswith("R32-")}
    for k in sorted(r32_matches.keys()):
        v = r32_matches[k]
        print(f'{k}: {v["home_team"]} vs {v["away_team"]} (state={v["state"]})')
else:
    print("No state file found")
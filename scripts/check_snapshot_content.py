"""Check what's in the latest snapshot."""
import json
from pathlib import Path

snapshots_dir = Path("output/snapshots")
snapshots = sorted([d for d in snapshots_dir.iterdir() if d.is_dir()])
latest = snapshots[-1]
print(f"Latest snapshot: {latest.name}")

# Check predictions
pred_file = latest / "predictions.json"
if pred_file.exists():
    preds = json.loads(pred_file.read_text())
    print(f"\nPredictions: {len(preds)} entries")
    stages = set()
    for p in preds:
        stages.add(p.get("stage", p.get("match_type", "unknown")))
    print(f"Stages: {stages}")
    for p in preds[:3]:
        print(f"  {p.get('match_id','?')}: {p.get('home_team','?')} vs {p.get('away_team','?')} ({p.get('stage',p.get('match_type','?'))})")
    if len(preds) > 3:
        print(f"  ... and {len(preds)-3} more")

# Check bracket data
bracket_file = latest / "bracket_data.json"
if bracket_file.exists():
    bracket = json.loads(bracket_file.read_text())
    ko = bracket.get("knockout", {})
    b = ko.get("bracket", {})
    print(f"\nBracket rounds:")
    for round_name, matches in b.items():
        print(f"  {round_name}: {len(matches)} matches")
        for m in matches[:2]:
            print(f"    {m.get('match_id','?')}: {m.get('home_team','?')} vs {m.get('away_team','?')} (winner: {m.get('winner','?')})")
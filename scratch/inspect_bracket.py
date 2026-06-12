"""Verify new bracket data has path labels and annex_c numbers."""
from src.visualization.bracket import load_latest_bracket

b = load_latest_bracket()
bracket = b["bracket"]

print("=== Round of 32 ===")
for m in bracket["round_of_32"]:
    mid = m["match_id"]
    annex = m.get("annex_c", "")
    home = m["home_team"]
    away = m["away_team"]
    hp = m.get("home_path", "")
    ap = m.get("away_path", "")
    winner = m.get("winner", "?")
    print(f"  {annex:5s} {home:20s} ({hp:4s}) vs {away:20s} ({ap:4s})  -> {winner}")

print("\n=== Round of 16 ===")
for m in bracket["round_of_16"]:
    annex = m.get("annex_c", "")
    home = m["home_team"]
    away = m["away_team"]
    hp = m.get("home_path", "")
    ap = m.get("away_path", "")
    winner = m.get("winner", "?")
    print(f"  {annex:5s} {home:20s} ({hp:6s}) vs {away:20s} ({ap:6s})  -> {winner}")

print("\n=== Quarter-finals ===")
for m in bracket["quarter_finals"]:
    annex = m.get("annex_c", "")
    home = m["home_team"]
    away = m["away_team"]
    hp = m.get("home_path", "")
    ap = m.get("away_path", "")
    winner = m.get("winner", "?")
    print(f"  {annex:5s} {home:20s} ({hp:6s}) vs {away:20s} ({ap:6s})  -> {winner}")

print("\n=== Semi-finals ===")
for m in bracket["semi_finals"]:
    annex = m.get("annex_c", "")
    home = m["home_team"]
    away = m["away_team"]
    hp = m.get("home_path", "")
    ap = m.get("away_path", "")
    winner = m.get("winner", "?")
    print(f"  {annex:5s} {home:20s} ({hp:6s}) vs {away:20s} ({ap:6s})  -> {winner}")

f = bracket["final"]
annex = f.get("annex_c", "")
hp = f.get("home_path", "")
ap = f.get("away_path", "")
print(f"\n  {annex:5s} {f['home_team']:20s} ({hp:6s}) vs {f['away_team']:20s} ({ap:6s})  -> {f.get('winner', '?')}")

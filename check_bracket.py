import json

d = json.load(open("output/snapshots/000_baseline/bracket_data.json"))

print("=== Champion Odds (top 10) ===")
odds = d["champion_odds"]
items = sorted(odds.items(), key=lambda x: x[1], reverse=True)
for t, p in items[:10]:
    print(f"  {t}: {p:.2%}")

print()
b = d["bracket"]
f = b["final"]
print("=== Final (last iteration) ===")
print(f"  {f['home_team']} {f['score']['home']} - {f['score']['away']} {f['away_team']}  (winner: {f['winner']})")

print()
print("=== Semi-Finals (last iteration) ===")
for s in b["semi_finals"]:
    print(f"  {s['home_team']} {s['score']['home']} - {s['score']['away']} {s['away_team']}  (winner: {s['winner']})")

print()
print("=== Config ===")
cfg = json.load(open("output/snapshots/000_baseline/config.json"))
print(f"  iterations: {cfg}")

"""Head to head historical matches helper."""

from __future__ import annotations

import pandas as pd

from src.config import RAW_MATCHES_FILE


def get_head_to_head(team_a: str, team_b: str) -> dict[str, object]:
    """Fetch recent historical matches and summary between two teams."""
    
    if not RAW_MATCHES_FILE.exists():
        return {"summary": {}, "recent_matches": []}

    # Load matches
    df = pd.read_csv(RAW_MATCHES_FILE)
    
    # Filter for head-to-head matches
    condition_1 = (df["home_team"] == team_a) & (df["away_team"] == team_b)
    condition_2 = (df["home_team"] == team_b) & (df["away_team"] == team_a)
    h2h_df = df[condition_1 | condition_2].copy()
    
    if h2h_df.empty:
        return {"summary": {}, "recent_matches": []}

    # Sort by date descending
    h2h_df["date"] = pd.to_datetime(h2h_df["date"])
    h2h_df = h2h_df.sort_values(by="date", ascending=False)
    
    wins_a = 0
    wins_b = 0
    draws = 0
    
    for _, row in h2h_df.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        home_goals = row["home_goals"]
        away_goals = row["away_goals"]
        
        if home_goals > away_goals:
            if home == team_a:
                wins_a += 1
            else:
                wins_b += 1
        elif away_goals > home_goals:
            if away == team_a:
                wins_a += 1
            else:
                wins_b += 1
        else:
            draws += 1
            
    summary = {
        team_a + "_wins": wins_a,
        team_b + "_wins": wins_b,
        "draws": draws,
        "total_matches": len(h2h_df)
    }
    
    # Return last 5 matches
    recent = []
    for _, row in h2h_df.head(5).iterrows():
        recent.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_goals": int(row["home_goals"]),
            "away_goals": int(row["away_goals"]),
            "tournament": row["tournament"]
        })
        
    return {"summary": summary, "recent_matches": recent}

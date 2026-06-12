import pandas as pd
from pathlib import Path
from src.config import SETTINGS, RAW_RANKINGS_FILE

def generate_mock_penalties():
    # Output file
    output_file = SETTINGS.raw_dir / "matches" / "historical_penalties.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load all World Cup teams
    rankings_df = pd.read_csv(RAW_RANKINGS_FILE)
    teams = rankings_df["team"].unique()
    
    # Specific realistic assignments
    # High proficiency
    high_perf = {"Argentina", "Germany", "Croatia", "Morocco", "Portugal"}
    # Low proficiency
    low_perf = {"Spain", "England", "Japan", "Netherlands", "Switzerland"}
    
    data = []
    for team in teams:
        if team in high_perf:
            won = 4
            lost = 1
        elif team in low_perf:
            won = 1
            lost = 4
        else:
            # Average/default
            won = 2
            lost = 2
            
        rate = won / (won + lost) if (won + lost) > 0 else 0.5
        
        data.append({
            "team": team,
            "shootouts_won": won,
            "shootouts_lost": lost,
            "penalty_win_rate": round(rate, 2)
        })
        
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    print(f"Generated historical penalties for {len(df)} teams at {output_file}")

if __name__ == "__main__":
    generate_mock_penalties()

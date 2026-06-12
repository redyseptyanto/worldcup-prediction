import pandas as pd
import re

def normalize_name(name):
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()

official = pd.read_csv(r'C:\Users\PSA-Airbyte\autodev\projects\worldcup-prediction\data\raw\players\official_2026_rosters.csv')
sofifa = pd.read_csv(r'C:\Users\PSA-Airbyte\autodev\projects\worldcup-prediction\data\raw\players\sofifa_players.csv', low_memory=False)

def match_team(team_name):
    off_team = official[official['team'] == team_name]
    sof_team = sofifa[sofifa['nationality_name'] == team_name]
    
    print(f"--- {team_name} ---")
    matched = 0
    for name in off_team['player_name']:
        norm_wiki = normalize_name(name)
        # Check if wiki name is in sofifa full_name or short_name
        # Simple token intersection
        wiki_tokens = set(norm_wiki.split())
        
        found = False
        for _, row in sof_team.iterrows():
            norm_full = normalize_name(row['long_name'])
            norm_short = normalize_name(row['short_name'])
            full_tokens = set(norm_full.split())
            short_tokens = set(norm_short.split())
            
            # If intersection is at least 2 words or 1 word if len is 1
            if len(wiki_tokens & full_tokens) >= max(1, len(wiki_tokens)-1) or len(wiki_tokens & short_tokens) >= max(1, len(wiki_tokens)-1):
                found = True
                break
        if found:
            matched += 1
        else:
            print(f"Missing: {name}")
    print(f"Matched {matched} out of {len(off_team)}")

match_team('Czech Republic')
match_team('Mexico')
match_team('South Africa')

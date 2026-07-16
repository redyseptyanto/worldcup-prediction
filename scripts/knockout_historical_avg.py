"""
Compute historical knockout-stage averages per team from historical_matches.csv.
==================================================================================
Output: team -> (avg_gf_knockout, avg_ga_knockout, matches_knockout)
"""

import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
matches = pd.read_csv(ROOT / 'data/raw/matches/historical_matches.csv')

# Filter to knockout stage matches only
knockout = matches[matches['stage'].isin(['knockout', 'knock-out', 'final', 'semi', 'quarter', 'round_of_16'])]

# Some datasets label differently — also include stage names with 'knock' or 'final'
if knockout.empty:
    # Fallback: use stage == 'historical' and round != 'group' patterns
    knockout = matches[
        (matches['stage'] == 'historical') &
        (~matches['round'].astype(str).str.startswith('group', na=False))
    ].copy()

print('Knockout matches:', len(knockout))
print('Columns:', list(knockout.columns))
print()

# Compute per-team knockout averages
home = knockout.groupby('home_team').agg(
    matches_home=('match_id', 'count'),
    avg_gf_home=('home_goals', 'mean'),
    avg_ga_home=('away_goals', 'mean'),
)

away = knockout.groupby('away_team').agg(
    matches_away=('match_id', 'count'),
    avg_gf_away=('away_goals', 'mean'),
    avg_ga_away=('home_goals', 'mean'),
)

combined = pd.concat([home, away], axis=1)
combined = combined.groupby(level=0).agg({
    'matches_home': 'sum',
    'matches_away': 'sum',
    'avg_gf_home': 'mean',
    'avg_gf_away': 'mean',
    'avg_ga_home': 'mean',
    'avg_ga_away': 'mean',
})
combined['matches'] = combined['matches_home'] + combined['matches_away']
combined['avg_gf'] = (combined['avg_gf_home'] + combined['avg_gf_away']) / 2
combined['avg_ga'] = (combined['avg_ga_home'] + combined['avg_ga_away']) / 2

combined = combined.sort_values('matches', ascending=False)
print('Top 20 teams by knockout matches:')
print(combined.head(20).to_string())
print()

# Show teams in the R32 bracket that have historical knockout data
r32_teams = [
    'South Africa', 'Canada', 'Germany', 'Paraguay', 'Netherlands', 'Morocco',
    'Brazil', 'Japan', 'France', 'Sweden', 'Ivory Coast', 'Norway', 'Mexico',
    'Ecuador', 'England', 'DR Congo', 'United States', 'Bosnia and Herzegovina',
    'Belgium', 'Senegal', 'Portugal', 'Croatia', 'Spain', 'Austria',
    'Switzerland', 'Algeria', 'Argentina', 'Cape Verde', 'Colombia', 'Ghana',
    'Australia', 'Egypt',
]

print('=== R32 teams with historical knockout data ===')
r32_data = combined.loc[combined.index.isin(r32_teams)]
print(r32_data.to_string())
print()

print('=== R32 teams WITHOUT historical knockout data ===')
missing = set(r32_teams) - set(r32_data.index)
print(sorted(missing))
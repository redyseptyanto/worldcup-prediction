import pandas as pd
from pathlib import Path

hist = pd.read_csv(Path('data/raw/matches/historical_matches.csv'))
print('Unique stages:', hist['stage'].unique()[:20])
print('Stage value counts:')
print(hist['stage'].value_counts().head(20))
print()
print('Unique rounds (sample):', hist['round'].dropna().unique()[:20])
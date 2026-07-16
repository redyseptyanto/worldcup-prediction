import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.data.fifa_official import load_official_tournament_form
import pandas as pd

# Load data
tournament_form = load_official_tournament_form()
group_lookup = {}
for row in tournament_form.itertuples(index=False):
    group_lookup[row.team] = {
        'gf_per_match': row.tournament_goals_for_per_match,
        'ga_per_match': row.tournament_goals_against_per_match,
    }

hist = pd.read_csv(ROOT / 'data/raw/matches/historical_matches.csv')
knockout_hist = hist[hist['stage'].isin(['knockout', 'knock-out', 'final', 'semi', 'quarter', 'round_of_16'])]
home_hist = knockout_hist.groupby('home_team').agg(h_gf=('home_goals', 'mean'), h_ga=('away_goals', 'mean'))
away_hist = knockout_hist.groupby('away_team').agg(a_gf=('away_goals', 'mean'), a_ga=('home_goals', 'mean'))
hist_combined = pd.concat([home_hist, away_hist], axis=1).groupby(level=0).agg('mean')
hist_lookup = hist_combined.to_dict('index')
league_avg_gf = tournament_form['tournament_goals_for_per_match'].mean()

def blended_goals(home, away):
    hg = group_lookup.get(home, {})
    ag = group_lookup.get(away, {})
    hh = hist_lookup.get(home, {})
    ah = hist_lookup.get(away, {})
    h_gf = 0.5 * hg.get('gf_per_match', league_avg_gf) + 0.5 * hh.get('h_gf', league_avg_gf)
    h_ga = 0.5 * hg.get('ga_per_match', league_avg_gf) + 0.5 * hh.get('h_ga', league_avg_gf)
    a_gf = 0.5 * ag.get('gf_per_match', league_avg_gf) + 0.5 * ah.get('a_gf', league_avg_gf)
    a_ga = 0.5 * ag.get('ga_per_match', league_avg_gf) + 0.5 * ah.get('a_ga', league_avg_gf)
    hx = max(0.3, min(2.0, (h_gf * a_ga) / league_avg_gf))
    ax = max(0.3, min(2.0, (a_gf * h_ga) / league_avg_gf))
    return round(hx, 2), round(ax, 2)

# Debug Germany vs Paraguay
h, a = blended_goals('Germany', 'Paraguay')
print('Germany vs Paraguay:')
print('  raw blended: ' + str(h) + '-' + str(a))
print('  rounded: ' + str(int(round(h))) + '-' + str(int(round(a))))

# Show inputs
hg = group_lookup.get('Germany', {})
hh = hist_lookup.get('Germany', {})
ag = group_lookup.get('Paraguay', {})
ah = hist_lookup.get('Paraguay', {})
print()
print('Germany group GF/GA:', hg.get('gf_per_match'), hg.get('ga_per_match'))
print('Germany hist GF/GA:', hh.get('h_gf'), hh.get('h_ga'))
print('Paraguay group GF/GA:', ag.get('gf_per_match'), ag.get('ga_per_match'))
print('Paraguay hist GF/GA:', ah.get('a_gf'), ah.get('a_ga'))
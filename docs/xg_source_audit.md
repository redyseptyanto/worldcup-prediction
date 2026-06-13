# Real xG Source Audit

This note evaluates whether the current project sources already contain **real expected-goals (xG)** data, and if not, which external sources are realistic candidates for adding it while still keeping **real historical scores** in the modeling pipeline.

## Current Repo Audit

The current repo **does not** contain real xG in its raw historical match source.

### Current historical match file

`data/raw/matches/historical_matches.csv`

Current columns:

- `match_id`
- `date`
- `stage`
- `round`
- `group`
- `home_team`
- `away_team`
- `home_goals`
- `away_goals`
- `tournament`
- `city`
- `country`
- `neutral`

There is no:

- `home_xg`
- `away_xg`
- shot-level event data
- xG-by-shot breakdown

### Current source inventory

The current pipeline uses:

- `martj42/international_results` for real historical scores
- computed rankings from those historical scores
- SOFIFA and Transfermarkt for squad/player context
- World Bank for macro context
- Open-Meteo for fixture weather context

Those sources are useful, but none of the current raw files provide a real xG field for historical international matches.

## Important Modeling Principle

If we add real xG, we should **not** replace actual scores with xG.

Both matter:

- actual scores tell us what really happened
- xG tells us the quality of chances created and conceded

That matters because:

- a team can win with low xG
- a team can lose while posting better xG
- repeated xG superiority often reflects underlying strength better than a single scoreline

So the best design is:

- keep real historical scores as the true outcome
- add real xG as an additional explanatory and predictive feature set

## Best External Source Candidates

### 1. StatsBomb Open Data

Source:

- https://github.com/statsbomb/open-data
- https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json

Why it is strong:

- primary-source event data
- shot-level event structure
- real xG is derivable or already embedded in event data for supported matches
- reproducible and research-friendly

Weakness:

- coverage is **not complete** for all international matches since 2018
- it covers selected competitions, not the full universe of friendlies and qualifiers

Current international competition coverage visible from the open-data competition inventory includes:

- FIFA World Cup 2018
- FIFA World Cup 2022
- UEFA Euro 2020
- UEFA Euro 2024
- Copa America 2024
- African Cup of Nations 2023

Conclusion:

- excellent **high-quality xG source**
- not enough by itself for full 2018-present international coverage

### 2. FiveThirtyEight international SPI archive

Source pattern:

- https://projects.fivethirtyeight.com/soccer-api/international/spi_matches_intl.csv
- archived through the Wayback Machine because the live endpoint is no longer reliably downloadable

Why it is strong:

- much broader international coverage than StatsBomb
- includes qualifiers, Nations League, Gold Cup, Copa America, African Cup of Nations, World Cup, and friendlies
- includes match-level `xg1` and `xg2`

Observed coverage from the latest usable archive snapshot:

- 4,647 international matches
- date range: 2019-01-02 through 2024-03-23
- 29 international competition labels

Weakness:

- archived source, not a currently maintained live feed
- xG is model-generated match data rather than shot-level event data
- coverage currently starts in 2019, not 2018

Conclusion:

- best available **broad-coverage xG source**
- should be treated as secondary to StatsBomb on overlapping matches

### 3. FootyStats international xG pages

Example:

- https://footystats.org/international/international-friendlies/xg

Why it is interesting:

- appears to expose xG and xGA for international competitions

Weakness:

- third-party aggregation
- less transparent provenance than StatsBomb
- less attractive as a core modeling source

Conclusion:

- possible fallback or validation source
- not my first choice for the main pipeline

## Recommendation

The strongest path is a **hybrid xG pipeline**:

1. keep the current real-score source as the canonical historical match record
2. add a sidecar xG dataset from external sources
3. join xG to historical matches when available
4. leave unmatched matches score-only rather than inventing fake xG

### Recommended source hierarchy

1. **StatsBomb Open Data** for high-quality tournament/event-level xG
2. **FiveThirtyEight international archive** for broader competition coverage such as qualifiers and friendlies
3. current historical scores dataset remains the canonical score/outcome layer

## Recommended Feature Strategy

Without touching the current Poisson model immediately, we should first build xG as a parallel feature layer.

Suggested features:

- `xg_for_avg`
- `xg_against_avg`
- `xg_diff`
- `recent_xg_for_avg`
- `recent_xg_against_avg`
- `recent_xg_diff`
- `xg_overperformance` = goals minus xG
- `xga_overperformance` = goals conceded minus xGA

For real head-to-head, we can calculate:

- `h2h_matches_since_2018`
- `h2h_wins`
- `h2h_draws`
- `h2h_losses`
- `h2h_goal_diff`
- `h2h_xg_diff` when xG exists

## How to Use H2H Safely

Historical H2H should be treated carefully, and in the current implementation it should remain **explanatory-only**.

Good use:

- explanatory section in matchup reports
- analyst-facing narrative context
- future validation experiments with a very small capped effect

Bad use:

- giving a large model weight to a tiny 2-match or 3-match sample

Best practice if we ever promote it into the model:

- weight H2H by recency
- weight H2H by sample size
- cap the maximum effect on the final prediction
- only keep it if backtests show incremental value beyond Elo, form, and xG

## Suggested Implementation Order

### Phase 1

- keep the current score pipeline untouched
- build a sidecar historical xG dataset from StatsBomb plus archived FiveThirtyEight
- join by team/date/score where possible, preferring StatsBomb on overlaps
- create an exploratory notebook to compare:
  - real scores
  - real xG
  - H2H score history
  - H2H xG history

### Phase 2

- add xG-based rolling features to the training dataset
- keep actual score outcome as the target
- compare model performance against the current baseline

### Phase 3

- optionally add limited H2H features
- only keep them if validation shows genuine lift

## Bottom Line

Current repo status:

- **real scores exist**
- **real xG does not exist**

Best next move:

- do **not** replace score data
- do **add** real xG as a parallel feature layer
- do **use** H2H history, but only lightly and carefully

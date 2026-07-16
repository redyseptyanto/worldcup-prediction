# Snapshot Calibration Guide — World Cup 2026 Prediction Model

This document explains the parameters, methodology, and learned adjustments for each
prediction snapshot from `000_baseline` through `006_blended_knockout_scores`.

---

## Quick Reference Table

| Snapshot | Descriptor | Key Parameters | When to Use |
|---|---|---|---|
| `000_baseline` | Pre-tournament baseline | Historical ensemble, default Poisson | Pre-tournament only |
| `001_after_group_stage_complete` | After all 72 real results ingested | Real results baked into features | Post-group, raw recalibration |
| `002_after_official_team_stats` | Adds FIFA official team stats | + `official_recent_form_index` etc. | Best winner accuracy (72.22%) |
| `003_knockout_calibrated` | Knocked-out (broken metadata) | Same as 001 but with calibration notes | **DEPRECATED — missing model signature** |
| `004_knockout_calibrated` | Correct knockout calibration | Slope 2.0, draw×0.7, lambda 0.5-2.0 | **Best calibrated knockout** |
| `005_blended_knockout_scores` | Based on 001 (uncalibrated) | Blended scores on top of slope 3.6 | **Skip — wrong base** |
| `006_blended_knockout_scores` | Based on 004 (calibrated) | Blended scores on top of slope 2.0 | Best blend of form + history |

**Recommended for knockout:** `006_blended_knockout_scores`
**Recommended for winner-only:** `004_knockout_calibrated`

---

## How Winner Predictions Work

### Ensemble Architecture

The model is a weighted ensemble of five sub-models:

| Sub-model | Weight | Role |
|---|---|---|
| Poisson score model | 0.28 | Generates expected-goals distribution → win/draw/loss probs |
| XGBoost classifier | 0.21 | Non-linear outcome classifier on feature diffs |
| Random forest | 0.17 | Tree-based outcome classifier, stabilizes against boosting |
| Elo model | 0.14 | Baseline strength from rating gap |
| xG outcome model | 0.20 | Outcome probabilities trained on expected-goals features |

Each sub-model outputs probabilities for `home_win`, `draw`, and `away_win`.
The ensemble combines them with the weights above, then applies a **logistic
transformation** to produce the final advancement probability:

```python
home_advance_prob = 1.0 / (1.0 + exp(-slope * power_diff))
```

### Knockout Calibration Changes

From the group-stage analysis (`notebooks/group_stage_prediction_analysis.ipynb`):

| Parameter | Baseline (001/002) | Calibrated (004/006) | Why Changed |
|---|---|---|---|
| Logistic slope | 3.6 | **2.0** | 3.6 produced extreme 85-15% probs for close knockout matches. Qualified teams are more balanced than group-stage mismatches. |
| Draw probability | raw | **× 0.7** | Knockout has fewer draws in regulation than group stage |
| Poisson lambda range | 0.5 – 2.5 | **0.5 – 2.0** | Tightens expected-goals variance for qualified teams only |
| xG features | optional | **included** | `official_recent_form_index` + tournament GF/GA per match |

### Feature Sources

The ensemble uses these feature categories:

1. **Elo / Ranking difference** — FIFA ranking points gap + computed Elo gap
2. **Form difference** — recent win rate, goals for/against per match
3. **Attack / Defense indices** — from official FIFA team stats tables
4. **World Cup pedigree** — semi-final rate, appearances, overall pedigree score
5. **Contextual factors** — squad rating, availability, rest days, travel fatigue, weather

For snapshots `002+`, features are augmented with `official_recent_form_index`
and related signals pulled from FIFA's official team-statistics pages.

---

## How Score Predictions Work

### Primary Mechanism: Poisson Distribution

The Poisson model estimates `expected_goals_home` and `expected_goals_away`
from team attacking/defending strength, then samples scorelines from that
distribution. The `most_likely_exact_score` is the mode of that distribution.

### Blended Override (005 / 006 only)

Starting with `005`, an additional score computation runs **after** the ensemble:

```
group_xg_home  = team_goals_for_per_match_in_groups
hist_xg_home   = team_avg_goals_scored_in_knockout_history
blended_home   = 0.5 * group_xg_home + 0.5 * hist_xg_home

home_expected = (blended_home * opponent_blended_away_ga) / league_avg
```

The result is clamped to `[0.3, 2.0]` and rounded to the nearest integer.

**Important caveat:** The historical knockout averages file (`historical_matches.csv`)
labels all matches as `stage=historical` with no group/knockout split. The "historical
knockout" averages are therefore **all-match averages** across every competition.
The blend is mathematically close to just using group-stage stats, which is why
003–006 showed near-identical scores until the damping/capping was applied.

### Why Exact Scores Have Low Confidence

From the group-stage backtest:

| Metric | Value |
|---|---|
| Winner accuracy | 72.22% |
| Score MAE (mean absolute error) | ~1.75 goals per match |
| Matches with exact score correct | ~15% |
| Blowouts (>4 total goals) missed | Most of them |

Poisson models are good at predicting *who will win* and *roughly how many goals*,
but poor at predicting the *exact* scoreline. A 2-1 and 1-0 both reflect similar
goal tallies but differ by one exact goal.

**Recommendation:** Trust winner probabilities and bracket progression more than
exact scores.

---

## Snapshot-by-Snapshot Breakdown

### 000_baseline

- **Descriptor:** `baseline`
- **Model:** Historical ensemble (no real results ingested)
- **Score model:** Default Poisson (lambda range 0.5 – 2.5)
- **Logistic slope:** 3.6 (default — too sharp for knockout)
- **Draw handling:** Raw draw probability from ensemble
- **Use case:** Pre-tournament predictions only

### 001_after_group_stage_complete

- **Descriptor:** `after_group_stage_complete`
- **Model:** Re-trained ensemble after ingesting all 72 real group results
- **Score model:** Default Poisson
- **Logistic slope:** 3.6 (unchanged)
- **Draw handling:** Raw draw probability
- **Use case:** Post-group recalibration using real match data

### 002_after_official_team_stats

- **Descriptor:** `after_official_team_stats`
- **Model:** Same as 001, plus features from FIFA official team-stat pages
- **Added features:** `official_recent_form_index`, `official_attack_signal`,
  `official_defense_signal`, `official_control_signal`, `official_xg_signal`
- **Score model:** Default Poisson
- **Logistic slope:** 3.6
- **Accuracy:** 72.22% winner accuracy (+1.4 pct points over 001)
- **Use case:** Best winner accuracy during group stage; still uses default slope

### 003_knockout_calibrated (DEPRECATED)

- **Descriptor:** `knockout_calibrated`
- **Issue:** Created with broken metadata — `model_metadata.signature` is MISSING
- **Parameters:** Slope 2.0, draw×0.7, lambda 0.5–2.0
- **Why broken:** `create_knockout_calibrated_snapshot.py` originally replaced
  `model_metadata` entirely with a calibration dict, dropping the `signature`
- **Use case:** Do not use — select 004 or 006 instead

### 004_knockout_calibrated

- **Descriptor:** `knockout_calibrated`
- **Base:** `001_after_group_stage_complete` (re-ingested with corrected metadata merge)
- **Logistic slope:** **2.0**
- **Draw probability multiplier:** **0.7**
- **Poisson lambda range:** **0.5 – 2.0**
- **Score model:** Default Poisson (clamped by lambda range)
- **Metadata:** Preserves original model signature (`9f5ad0b91383`)
- **Use case:** **Best calibrated winner probabilities for knockout stage**

### 005_blended_knockout_scores

- **Descriptor:** `blended_knockout_scores`
- **Base:** `001_after_group_stage_complete` (uncalibrated slope 3.6)
- **Score model:** Blended 0.5×group_xG + 0.5×historical_knockout_avg
- **Issue:** Wrong base — uses old slope 3.6, so winner probs are overconfident
- **Use case:** Skip — winner probabilities are not properly calibrated

### 006_blended_knockout_scores (RECOMMENDED)

- **Descriptor:** `blended_knockout_scores`
- **Base:** `004_knockout_calibrated` (slope 2.0, draw×0.7)
- **Score model:** Blended 0.5×group_xG + 0.5×all-match_hist_avg, clamped [0.3, 2.0]
- **Logistic slope:** 2.0 (inherited from 004)
- **Draw probability:** ×0.7 (inherited)
- **Use case:** Best available snapshot — calibrated winner probs + blended scores

---

## Formulas Reference

### Winner Probability (Knockout)

```
diff = home_power - away_power
home_advance_prob = 1 / (1 + exp(-2.0 * diff))
away_advance_prob = 1 - home_advance_prob
```

Where `home_power` is the ensemble's `recent_power` score derived from
official recent-form indices.

### Blended Expected Goals (005/006 only)

```
group_xg = tournament_goals_for_per_match   # from FIFA official standings
hist_xg  = historical_avg_goals_in_knockout # from historical_matches.csv

blended_gf = 0.5 * group_xg + 0.5 * hist_xg
blended_ga = 0.5 * group_ga + 0.5 * hist_ga

home_xg = (blended_home_gf * blended_away_ga) / league_avg
away_xg = (blended_away_gf * blended_home_ga) / league_avg

clamped_home = max(0.3, min(2.0, home_xg))
clamped_away = max(0.3, min(2.0, away_xg))
```

`league_avg` = mean of `tournament_goals_for_per_match` across all 48 teams
(currently ~1.49).

---

## Known Limitations

1. **Historical knockout averages are not truly knockout-filtered.** The
   `historical_matches.csv` file uses `stage=historical` for every row, with no
   group/knockout distinction. The "historical knockout" blend is therefore an
   all-competition average — the same signal the ensemble already captures.

2. **Exact score confidence remains low.** Even with blending, group-stage
   backtest showed ~1.75 goals MAE. Treat displayed scorelines as directional.

3. **Draw model is still weak.** The ×0.7 multiplier reduces draw probability
   but does not fix the underlying draw-detection problem. The model still
   struggles with evenly-matched teams.

4. **FIFA detailed stats API returns 403.** When `load_official_team_stats()`
   returns empty, the system falls back to tournament-form-only features. This
   is handled gracefully but reduces feature richness for some teams.

---

## Files Referenced

| File | Purpose |
|---|---|
| `scripts/create_knockout_calibrated_snapshot.py` | Creates 004 from 001 |
| `scripts/create_blended_knockout_snapshot.py` | Creates 006 from 004 |
| `scripts/xg_score_calibration.py` | Standalone xG + damping POC |
| `scripts/knockout_historical_avg.py` | Computes historical per-team averages |
| `scripts/blended_knockout_predictor.py` | In-place score override on 004 |
| `notebooks/group_stage_prediction_analysis.ipynb` | Full analysis with plotly charts |
| `notebooks/official_recent_stats_knockout_projection.ipynb` | Pure recent-stats notebook |
| `docs/group_stage_analysis_report.md` | Detailed group-stage findings |
| `data/raw/matches/historical_matches.csv` | All historical internationals |
| `data/external/fifa_official_team_stats.csv` | FIFA official stats (often empty) |

---

## Changelog

| Date | Change |
|---|---|
| 2026-06-29 | Initial analysis — draw blindness, score compression found |
| 2026-06-29 | Created 001 (ingest), 002 (+FIFA stats), 003 (broken metadata) |
| 2026-06-29 | Created 004 with slope 2.0, draw×0.7, lambda 0.5–2.0 |
| 2026-06-29 | Created 005 (wrong base), 006 (correct base) with blended scores |
| 2026-06-30 | Documented all snapshots, formulas, and limitations |
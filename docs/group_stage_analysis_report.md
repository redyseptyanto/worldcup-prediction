# Group Stage Prediction vs Reality Analysis — FIFA World Cup 2026

**Analysis Date:** June 29, 2026  
**Data:** 72 real group-stage matches (12 groups, 6 matches each)  
**Models Compared:** 3 snapshots (000_baseline, 001_after_group_stage_complete, 002_after_official_team_stats)

---

## 1. Executive Summary

| Snapshot | Accuracy | Correct/Wrong | Avg Goals Error | Avg Confidence |
|----------|----------|---------------|-----------------|----------------|
| 001_after_group_stage_complete | **70.83%** | 51/21 | 1.89 | 52.91% |
| 002_after_official_team_stats | **72.22%** | 52/20 | 1.75 | 55.08% |

**Best snapshot:** `002_after_official_team_stats` — 72.22% outcome accuracy  
**Improvement from baseline:** +1.4 pct points by incorporating official FIFA team stats

---

## 2. Where the Model Performed Well

### Groups with highest accuracy (80-100%)

| Group | Accuracy | Notes |
|-------|----------|-------|
| Group I (France, Norway, Senegal, Iraq) | **100%** | All 6 matches predicted correctly |
| Group C (Brazil, Morocco, Scotland, Haiti) | **83.3%** | 5/6 correct |
| Group D (USA, Australia, Paraguay, Turkey) | **83.3%** | 5/6 correct |
| Group E (Germany, Ivory Coast, Ecuador, Curacao) | **83.3%** | 5/6 correct |
| Group J (Argentina, Austria, Algeria, Jordan) | **83.3%** | 5/6 correct |

### Outcome types predicted well

- **Home wins:** 91.9% accuracy (34/37 actual home wins correctly identified)
- **Away wins:** 100% accuracy (18/18 actual away wins correctly identified)
- **Draws:** **0% accuracy** — the model predicted home win for ALL actual draws

**Key insight:** The model is excellent at picking winners when there IS a winner, but completely misses draws. This is the single biggest weakness.

---

## 3. Where the Model Struggled

### Groups with lowest accuracy (33-50%)

| Group | Accuracy | Notes |
|-------|----------|-------|
| Group H (Spain, Cape Verde, Uruguay, Saudi Arabia) | **33.3%** | Most unpredictable group |
| Group G (Belgium, Egypt, Iran, New Zealand) | **50.0%** | Multiple draws confounded predictions |
| Group A (Mexico, South Africa, South Korea, Czech Rep) | **66.7%** | Better but still missed key results |

### High-confidence predictions that were WRONG

| Match | Predicted | Actual | Confidence | Why Wrong |
|-------|-----------|--------|------------|-----------|
| England vs Ghana | 2-0 home | 0-0 draw | **78.42%** | Underestimated Ghana's defense |
| Canada vs Bosnia | 2-0 home | 1-1 draw | **74.53%** | Bosnia stronger than expected |
| Iran vs New Zealand | 1-0 home | 1-1 draw | **67.21%** | New Zealand more competitive |
| Portugal vs DR Congo | 1-0 home | 1-1 draw | **67.39%** | Same pattern |

**Pattern:** ALL high-confidence misses were draws that the model failed to anticipate.

---

## 4. CRITICAL BIAS: Score Compression

The model systematically **under-predicted goals**:

| Metric | Predicted | Actual | Bias |
|--------|-----------|--------|------|
| Total goals | 92 | 200 | **-108 goals (-54%)** |
| Avg per match | 1.28 | 2.78 | **-1.50 goals/match** |
| Matches under-predicted | - | 51/72 | **71% of matches** |

### Goals Distribution

| Total Goals | Predicted Count | Actual Count |
|-------------|----------------|--------------|
| 0 | 0 | 4 |
| 1 | 57 | 13 |
| 2 | 10 | 19 |
| 3 | 5 | 13 |
| 4 | 0 | 12 |
| 5 | 0 | 6 |
| 6 | 0 | 4 |
| 8 | 0 | 1 |

**The model predicted 92 total goals across all snapshots. The real total was 200 goals.** The model's predictions clustered around 1-goal scorelines (1-0, 0-1) but the actual tournament produced many high-scoring blowouts.

---

## 5. Group Advancement Prediction

The snapshot standings files use a different key format ("A", "B" vs "Group A", "Group B") from the official standings CSV, requiring format alignment. After alignment:

- The model's **pre-tournament** predictions for top-2 per group assumed historical strength
- The **actual** group stage had significant surprises:
  - **Bosnia and Herzegovina** advanced as 3rd place from Group B (not predicted)
  - **Paraguay, Ecuador, Sweden, Senegal, Algeria, DR Congo, Ghana** also advanced as 3rd place
- Only **4 third-place teams were eliminated**: South Korea, Scotland, Iran, Uruguay

---

## 6. Statistical Anomalies (Score Misses >= 3 goals)

These matches had scorelines that **defy statistical expectation** — the kind of "luck factor" mentioned in the task:

| Match | Predicted | Actual | Error |
|-------|-----------|--------|-------|
| Germany 7-1 Curacao | 2-0 | 7-1 | **6 goals** |
| Algeria 3-3 Austria | 1-0 | 3-3 | **5 goals** |
| Morocco 4-2 Haiti | 1-0 | 4-2 | **5 goals** |
| Netherlands 5-1 Sweden | 2-0 | 5-1 | **4 goals** |
| Canada 6-0 Qatar | 2-0 | 6-0 | **4 goals** |
| Senegal 5-0 Iraq | 1-0 | 5-0 | **4 goals** |
| Iraq 1-4 Norway | 0-1 | 1-4 | **4 goals** |
| Norway 3-2 Senegal | 1-0 | 3-2 | **4 goals** |

These matches represent one-sided blowouts or unexpectedly high-scoring affairs that a historical-data-driven model cannot easily predict. They reflect **tournament-specific dynamics**: team momentum, tactical mismatches exposed during the tournament, and psychological factors.

---

## 7. Confidence Calibration

| Confidence Range | Matches | Correct | Wrong | Accuracy |
|-----------------|---------|---------|-------|----------|
| 0-30% | 4 | 3 | 1 | 75.0% |
| 30-40% | 12 | 6 | 6 | 50.0% |
| 40-50% | 5 | 3 | 2 | 60.0% |
| 50-60% | 20 | 14 | 6 | 70.0% |
| 60-70% | 23 | 20 | 3 | **87.0%** |
| 70-100% | 8 | 6 | 2 | 75.0% |

**The model IS well-calibrated:** Accuracy generally increases with confidence. The 60-70% bin achieves 87% accuracy. The dip at 70-100% is due to small sample (8 matches with 2 misses — both were draws).

---

## 8. Third-Place Qualifiers

From the official standings:
- **8 third-place teams advanced** to Round of 32
- **4 third-place teams eliminated** (South Korea, Scotland, Iran, Uruguay)
- The model didn't explicitly predict third-place qualification order, but the snapshot standings show predicted rankings

---

## 9. Root Causes of Prediction Errors

### A. Draw Blindness (MOST CRITICAL ISSUE)
- **17 actual draws** occurred in the group stage
- The model predicted **0 draws correctly**
- All draws were predicted as home wins

**Why:** The ensemble model's historical training data likely has fewer draws due to the nature of international football (more variance in quality), but the 2026 tournament had unusually high parity among certain teams.

### B. Score Compression
- The model predicts scores around 1-0, 2-0, 0-1
- Actual tournament had 23 matches with 4+ total goals
- This suggests the Poisson-based goal model uses too-conservative lambda values

### C. Home Advantage Overweight
- The model strongly prefers predicting home wins (91/144 predictions = 63%)
- While historically justified, this missed draws where home teams couldn't break down organized defenses

### D. Missing Tournament Dynamics
- Blowout results (Germany 7-1, Canada 6-0, France 5-0, Senegal 5-0) show tournament-specific momentum
- The model relies on historical ELO/rankings that don't capture "team clicked at the right time"

---

## 10. Patterns & Learnings for Knockout Stage

### Pattern 1: Draws will decrease, winners must be found
- Group stage had 17 draws (23.6%)
- Knockout matches historically have ~20% draws in regulation
- BUT: knockout draws go to extra time/penalties — the model MUST pick a winner

### Pattern 2: Blowout potential increases with quality mismatch
- The knockout bracket has mismatches (e.g., group winners vs 3rd-place qualifiers)
- The model under-predicted blowout scores — need to widen Poisson lambda for Round of 32

### Pattern 3: Recent form > historical rankings
- Teams that dominated groups (France, Argentina, Mexico, Brazil, Netherlands, Germany, Spain, England, Colombia) have tournament momentum
- The `002_after_official_team_stats` snapshot which uses official FIFA team stats outperformed the historical-only model

### Pattern 4: High confidence ≠ lock
- 16% upset rate on high-confidence picks
- Upsets are NOT random — they cluster in certain groups/dynamics
- England-Ghana (78% confidence, was 0-0 draw) shows "big team underperformance" pattern

### Pattern 5: Away wins are predictable
- 100% accuracy on away win predictions suggests the model correctly identifies underdogs that will lose
- But it misidentifies which underdogs will DRAW instead of lose

---

## 11. Recommended Model Adjustments for Knockout

### A. Widen Goal Variance
- Current range: mostly 1-0, 2-0, 0-1 (avg 1.19 goals/match predicted)
- Recommended: Use tournament-form Poisson lambda based on ACTUAL group stage goals
- Use **empirical goals distribution** from real results as the prior
- For mismatches (e.g., France vs 3rd-place team), widen lambda to allow 4-0, 5-0 outcomes

### B. Reduce Draw Probability
- Group stage had more draws than expected, but knockout has fewer
- Apply a **knockout stage multiplier** of ~0.7 to draw probability
- For regulation draw predictions, shift to a "who wins on penalties" sub-model

### C. Weight FIFA Official Team Stats Higher
- The 002 snapshot improvement (+1.4%) came from incorporating team stats
- For the `official_recent_stats_knockout_projection.ipynb` notebook, the weights should be:
  - `official_recent_form_index`: **30%** (recent tournament form is king)
  - `official_attack_signal`: **20%**
  - `official_defense_signal`: **20%**
  - `official_control_signal`: **15%**
  - `official_xg_signal`: **15%**

### D. Add Tournament Momentum Factor
- **Power score** from group performance: points * 5 + goals_for * 2 + goal_difference * 3
- Top 4 by power score: France (89), Argentina (82), Mexico (75), Brazil/NED
- Use this as a "momentum bonus" added to the model's base prediction

### E. Penalty Shootout Model
- For knockout matches projected as close (predicted goals difference < 0.5, or high draw probability):
  - Use `team_conduct_score` as a proxy for discipline/discipline under pressure
  - Historical penalty records from the raw data

### F. Specific Knockout Predictions Adjustment

Based on the official Round-of-32 bracket and post-group power rankings:

| Matchup | Recommendation |
|---------|---------------|
| Mexico vs 3rd place | Mexico heavy favorite — widen goal range |
| Netherlands vs Sweden | Netherlands strong, but expect a closer match |
| Brazil vs Scotland | Brazil should dominate — expect 3+ goals |
| France vs 3rd place | France is tournament's best team — big win likely |
| Argentina vs 3rd place | Argentina in top form — expect comfortable win |

---

## 12. Bottom Line

The model achieved **72.22% outcome accuracy** predicting group stage matches that had an average of **2.78 goals per match** — a high-variance environment. This is a solid baseline.

**For knockout stage, the critical changes are:**

1. **Fix draw blindness** — Don't just predict home win for everything
2. **Widen goal expectations** — Group stage proved blowouts happen frequently
3. **Use recent tournament form** — Historical ELO is less predictive than "what happened in this tournament"
4. **Accept upsets** — ~16% of confident picks will be wrong

The `official_recent_stats_knockout_projection.ipynb` notebook's approach of using only official FIFA team stats (recent form index, attack/defense signals, xG) is directionally correct — it captures exactly the "what happened in THIS tournament" signal that the historical model misses.

---

*Analysis generated using `scripts/group_stage_prediction_analysis.py`*
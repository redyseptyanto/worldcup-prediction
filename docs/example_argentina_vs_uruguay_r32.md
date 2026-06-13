# Example Matchup: Argentina vs Uruguay in the Round of 32

This document explains how the current model would evaluate a hypothetical **Round of 32** match between **Argentina** and **Uruguay**, with **Argentina treated as the home side**.

## Short Answer

Under the current model, **Argentina is favored to advance**.

Current simulated outputs:

| Metric | Argentina | Uruguay |
|---|---:|---:|
| Regulation win probability | **56.39%** | 16.65% |
| Draw probability | 26.96% | - |
| Penalty win probability if drawn | **74.17%** | 25.83% |
| Total advancement probability | **76.39%** | 23.61% |
| Adjusted expected goals | **1.200** | 0.655 |
| Representative scoreline | **1-0** | - |

Advancement is computed as:

`P(advance) = P(win in regulation) + P(draw) * P(win on penalties)`

For Argentina:

`0.5639 + 0.2696 * 0.7417 = 0.7639`

## How the Model Reaches That Answer

The knockout simulator does **not** directly say "Argentina is better, so Argentina wins." It runs in three layers:

1. Build a pre-match prediction with the ensemble model.
2. Adjust that prediction using squad, injury, manager, tactical, macro, and fixture context.
3. Sample goals from the adjusted expected-goals rates. If the match is tied, resolve penalties.

## Layer 1: Ensemble Model Weights

The ensemble combines four model components:

| Component | Weight |
|---|---:|
| Poisson score model | **0.35** |
| Boosted classifier | **0.25** |
| Random forest | **0.20** |
| Elo model | **0.20** |

### What each model is doing

#### Poisson score model

The Poisson model is the score-engine of the stack. It estimates each team's expected goals from attacking and defensive strength, then converts those scoring rates into a full scoreline distribution.

In practical terms:

- stronger attack raises a team's expected goals
- weaker opposing defense also raises expected goals
- the model sums all likely scorelines to get win, draw, and loss probabilities

This model is useful because it is the most directly connected to plausible football scores such as `1-0`, `1-1`, or `2-1`.

#### Boosted classifier

The boosted model is a gradient-boosting classifier trained on the feature differences between the two teams. It learns non-linear decision patterns from the training data.

In practical terms:

- it can learn combinations such as "strong ranking edge plus strong form edge"
- it is less tied to score mechanics and more tied to match-outcome classification
- it often reacts strongly to features like ranking difference and Elo difference

This model is useful because it can capture more complex patterns than a simple formula.

#### Random forest

The random forest model is another outcome classifier, but instead of boosting sequential trees, it averages many decision trees built on random feature subsets.

In practical terms:

- it tends to be more stable and less brittle than one single tree
- it captures threshold-like logic such as "if Elo edge is big enough, home win becomes much more likely"
- it provides a second machine-learning opinion that is structurally different from boosting

This model is useful because it reduces dependence on any one modeling style.

#### Elo model

The Elo model is the most interpretable component. It converts the Elo rating gap between the two teams into win and loss probabilities, with a fixed draw mechanism.

In practical terms:

- if Team A has a much higher Elo than Team B, Team A gets a higher win probability
- if the Elo gap is small, the match becomes more balanced
- draw probability shrinks as the Elo gap gets larger

This model is useful because it gives a clean baseline view of relative team strength.

#### Why combine them?

Each model sees the matchup a bit differently:

- Poisson focuses on scoring mechanics
- boosted focuses on learned outcome patterns
- random forest adds a second tree-based view
- Elo gives a simple strength baseline

The ensemble is meant to be more robust than any single model on its own.

### Submodel probabilities for Argentina vs Uruguay

| Model | Argentina win | Draw | Uruguay win |
|---|---:|---:|---:|
| Poisson | 50.53% | 30.18% | 19.29% |
| Boosted | 60.34% | 30.33% | 9.33% |
| Random forest | 68.08% | 22.69% | 9.23% |
| Elo | 59.28% | 18.36% | 22.37% |

### Weighted ensemble before contextual adjustment

| Outcome | Weighted probability |
|---|---:|
| Argentina win | **58.24%** |
| Draw | 26.35% |
| Uruguay win | 15.41% |

This is the base opinion before squad and context adjustments are applied.

## Layer 2: Match Features Fed Into the Core Models

The core diff features for this matchup are:

| Feature | Value | Interpretation |
|---|---:|---|
| Elo difference | **+169.30** | Strong edge to Argentina |
| Ranking difference | **+151.66** | Strong edge to Argentina |
| Goals-for difference | **+0.645** | Argentina scores more recently |
| Goals-against difference | **-0.198** | Argentina concedes less recently |
| Form difference | **+0.569** | Better recent form for Argentina |
| Attack difference | **+0.645** | Better attacking profile for Argentina |
| Defense difference | **+0.198** | Better defensive profile for Argentina |
| World Cup pedigree difference | **+0.3715** | Stronger tournament history |
| World Cup semi-final rate difference | **+0.5714** | Better deep-run history |
| World Cup appearances difference | 0.0000 | No edge |

## Which Core Features Matter Most

The tree models do not currently expose exact local SHAP-style explanations for one single match, but they do expose **global feature importance**. That tells us which features those models usually lean on most.

### Boosted model feature importance

| Feature | Importance |
|---|---:|
| Ranking difference | **0.7235** |
| Elo difference | 0.1177 |
| Goals-against difference | 0.0530 |
| Defense difference | 0.0220 |
| Form difference | 0.0204 |
| Goals-for difference | 0.0213 |
| Attack difference | 0.0200 |
| World Cup pedigree difference | 0.0124 |
| World Cup appearances difference | 0.0076 |
| World Cup semi-final rate difference | 0.0021 |

### Random forest feature importance

| Feature | Importance |
|---|---:|
| Ranking difference | **0.4078** |
| Elo difference | **0.3382** |
| Goals-against difference | 0.0731 |
| Form difference | 0.0525 |
| Goals-for difference | 0.0521 |
| World Cup appearances difference | 0.0218 |
| Defense difference | 0.0205 |
| Attack difference | 0.0170 |
| World Cup pedigree difference | 0.0149 |
| World Cup semi-final rate difference | 0.0022 |

### Practical reading

For this specific matchup, the biggest reasons Argentina is ahead in the core models are:

- Argentina has a large **ranking** edge.
- Argentina has a large **Elo** edge.
- Argentina also has better **recent scoring**, **recent form**, and **attack/defense** numbers.
- Argentina has a stronger **World Cup pedigree** profile.

## Layer 3: Contextual Adjustment Weights

After the base ensemble is computed, the model applies a second adjustment layer. This layer changes both the win/draw/loss probabilities and the expected goals.

For this hypothetical example, there is **no fixed match id**, so:

- rest-day context is neutral
- travel-fatigue context is neutral
- weather context is neutral

Those terms therefore contribute `0.0000` here.

### Context contribution table

Positive values help Argentina. Negative values help Uruguay.

| Context factor | Contribution to `home_edge` | Interpretation |
|---|---:|---|
| Squad average rating | **+0.0123** | Argentina stronger overall squad |
| Starting XI rating | **+0.0085** | Argentina stronger likely XI |
| Squad market value | **+0.0041** | Small edge to Argentina |
| Availability score | **-0.0287** | Uruguay currently healthier / more available |
| Injury load | **-0.0245** | Argentina carries more recent injury burden |
| International experience | **+0.0073** | Small edge to Argentina |
| Manager continuity | **-0.0263** | Uruguay more stable here |
| Tactical balance | **-0.0140** | Uruguay better on this metric |
| Macro strength | **+0.0065** | Small edge to Argentina |
| Rest-day difference | 0.0000 | Neutral in this hypothetical |
| Travel-fatigue difference | 0.0000 | Neutral in this hypothetical |

### Net contextual effect

The total contextual edge is:

`home_edge = -0.0549`

That means the contextual layer actually pulls **slightly against Argentina**, even though Argentina remains the favorite overall.

This is important:

- the **core football strength metrics** strongly favor Argentina
- the **health/availability/continuity/tactical context** softens that advantage

## Effect on Probabilities

The contextual layer moves the probabilities like this:

| Stage | Argentina win | Draw | Uruguay win |
|---|---:|---:|---:|
| Before contextual adjustment | **58.24%** | 26.35% | 15.41% |
| After contextual adjustment | **56.39%** | 26.96% | 16.65% |

So Argentina remains favored, but by a bit less than the raw ensemble first suggested.

## Effect on Expected Goals

Base Poisson expected goals:

| Team | Base xG |
|---|---:|
| Argentina | **1.230** |
| Uruguay | 0.639 |

After contextual adjustment:

| Team | Adjusted xG |
|---|---:|
| Argentina | **1.200** |
| Uruguay | 0.655 |

Again, Argentina stays ahead, but the context layer narrows the gap slightly.

## Penalties

If the match is tied after regular time, the model uses penalty history and a small Elo component.

Penalty inputs:

| Input | Argentina | Uruguay |
|---|---:|---:|
| Penalty win rate | **0.80** | 0.50 |
| Elo | **1917.25** | 1747.95 |

Resulting penalty win probability:

| Team | Penalty win probability |
|---|---:|
| Argentina | **74.17%** |
| Uruguay | 25.83% |

This is a major reason Argentina's **advancement probability** is much higher than its regulation-only win probability.

## Final Interpretation

If Argentina meets Uruguay in the Round of 32, the current model says:

- Argentina is the better team on the main football-strength signals.
- Ranking difference and Elo difference are the biggest structural reasons.
- Argentina also carries better recent attack, form, and tournament-history signals.
- Uruguay recovers some ground through better availability, lower injury load, stronger continuity, and better tactical-balance metrics.
- Even after those adjustments, Argentina still projects as the favorite.
- If the match reaches penalties, Argentina becomes an even stronger favorite to advance.

## Important Caveat

This is a **hypothetical explanation**, not a locked tournament fixture explanation. Because there is no actual `match_id` attached here:

- venue-specific weather is not applied
- exact rest-day differences are not applied
- exact travel-fatigue values are not applied

If this matchup becomes a real bracket fixture later, the same teams could get slightly different probabilities once the true match context is known.

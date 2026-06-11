# Product Requirements Document

## 1. Objective

Build a local-first football prediction system that can:

- estimate match outcomes and scorelines
- simulate a tournament repeatedly
- adapt future predictions after real results are ingested
- preserve prediction history through immutable snapshots

This repository now implements a baseline version of that product.

## 2. Current Product Status

### Implemented

- cached real historical data collection
- multi-source feature engineering from historical, player, injury, market value, weather, travel, rest, manager, tactical, and macro datasets
- four-model ensemble
- full 48-team tournament simulation with 12 groups of four, best third-placed qualification, and a round of 32
- adaptive result ingest and snapshotting
- rollback and comparison utilities
- FastAPI interface
- optional Streamlit dashboard
- automated tests

### Deferred

- live result collection beyond the cached historical dataset
- PostgreSQL persistence
- Airflow orchestration
- production visualization assets

## 3. Product Scope For This Baseline

The baseline is intentionally constrained so we have a truthful, runnable system.

### Tournament Scope

- 12 groups of 4 teams
- top 2 teams plus the best 8 third-placed teams qualify
- round of 32, round of 16, quarter-finals, semi-finals, third-place match, and final determine the champion

### Persistence Scope

- cached raw inputs under `data/raw/`
- processed artifacts under `data/processed/`
- trained model artifact under `models/`
- state and snapshots under `output/`

### Interface Scope

- CLI-first workflow
- REST API for core operations
- optional Streamlit dashboard for inspection

## 4. Users

Primary users for the baseline:

- developers extending the platform
- analysts experimenting with tournament logic
- operators testing adaptive ingest and snapshot behavior

## 5. Functional Requirements

### 5.1 Data Collection

The system must:

- download and cache a real historical match dataset
- cache the current 2026 World Cup group-stage field and fixture list
- cache bracket rules for best third-placed qualification in the round of 32
- generate a small auto-results file for scheduler demos

### 5.2 Feature Engineering

The system must build match-level features that include:

- Elo difference
- ranking difference
- recent goals-for difference
- recent goals-against difference
- recent form difference
- attack difference
- defense difference
- player availability and injury load
- squad value and player-rating strength
- rest-day and travel-fatigue context
- weather context
- manager continuity and tactical-balance features
- macro country indicators

### 5.3 Prediction

The system must produce for each fixture:

- predicted scoreline
- home win probability
- draw probability
- away win probability
- confidence score and label

### 5.4 Simulation

The system must:

- simulate group-stage results from expected goals
- rank 4-team groups by points, goal difference, and goals scored
- rank third-placed teams across groups
- simulate a knockout path from group qualifiers
- estimate champion odds over repeated iterations

### 5.5 Adaptive Updates

The system must:

- track match states in a file-backed store
- reject duplicate ingest for resolved matches
- re-simulate after ingest
- write immutable snapshots
- compare snapshots
- support rollback to a prior snapshot state

### 5.6 API

The API must expose:

- service health
- single-match prediction
- tournament simulation
- team summary access
- feature importance access
- result ingest
- match state listing
- snapshot listing

## 6. Non-Functional Requirements

- deterministic outputs when using the project seed
- local execution after the initial historical data download
- clear filesystem outputs for debugging
- tests must pass in a clean checkout after setup

## 7. Data Model

### Raw Inputs

- `historical_matches.csv`
- `team_rankings.csv`
- `worldcup_fixtures.csv`
- `auto_results.csv`

### Processed Outputs

- `data/processed/datasets/train.csv`
- `data/processed/features/team_features.json`

### Runtime Outputs

- `models/ensemble.pkl`
- `output/predictions.csv`
- `output/simulation_results.json`
- `output/prediction_ledger.csv`
- `output/snapshots/<snapshot_id>/...`

## 8. Architecture

```text
Cached real historical data
  -> loaders and preprocessing
  -> feature engineering
  -> ensemble training
  -> tournament simulation
  -> API and adaptive workflows
  -> snapshots and reports
```

### Module Map

```text
src/
|- config.py
|- data/
|- features/
|- models/
|- simulation/
|- adaptive/
|- api/
|- scheduler/
`- visualization/
```

## 9. Model Design

### 9.1 Ensemble Components

- Poisson score model
- gradient boosting classifier in the `xgboost_model.py` slot
- random forest classifier
- Elo probability model

### 9.2 Weighting

Current default weights:

- Poisson: 0.35
- Boosted: 0.25
- Random forest: 0.20
- Elo: 0.20

### 9.3 Confidence

Confidence is derived from:

- ensemble agreement
- margin between the top two probabilities

The output is mapped to:

- Very High
- High
- Moderate
- Low
- Very Low

## 10. Adaptive Engine Design

### State Machine

Supported states:

- `PENDING`
- `RESOLVED`
- `POSTPONED`

### Snapshot Rules

Each snapshot contains:

- `snapshot.json`
- `predictions.json`
- `bracket_data.json`
- `standings.json`
- `team_features.json`
- `state.json`
- `config.json`

Snapshots are append-only.

### Rollback Rule

Rollback restores the saved match state from a selected snapshot, then creates a new snapshot representing the rolled-back branch.

## 11. Scheduler Design

The current scheduler is an offline demo.

It:

1. reads `data/external/auto_results.csv`
2. filters rows whose availability time has passed
3. ingests those results
4. writes a daily markdown report

This is a placeholder for future live-source automation.

## 12. API Contract

Implemented endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | health check |
| `/predict/match` | POST | predict one match |
| `/predict/bracket` | GET | run a tournament prediction |
| `/simulate/run` | POST | run tournament simulation with custom iterations |
| `/simulate/results` | GET | get a fresh simulation payload |
| `/teams` | GET | list team summary data |
| `/feature-importance` | GET | expose model feature importance |
| `/ingest/result` | POST | ingest one real result |
| `/state/matches` | GET | list current match states |
| `/snapshots` | GET | list stored snapshots |

## 13. Testing Requirements

The repository must keep passing:

```bash
pytest tests/
```

The tests must cover:

- raw data and loaders
- feature artifact generation
- ensemble probability validity
- simulation behavior
- adaptive snapshot creation
- API smoke behavior
- documentation consistency checks

## 14. Delivery Criteria For This Phase

This baseline phase is complete when:

1. `python -m src.data.collector --all --refresh` succeeds
2. `python -m src.features.build_features` succeeds
3. `python -m src.models.train --all` succeeds
4. `python -m src.simulation.tournament --iterations 50` succeeds
5. adaptive ingest creates a new snapshot
6. `pytest tests/` passes

## 15. Roadmap

### Phase 2

- extend knockout-stage context features beyond the group phase
- improve source coverage and calibration reporting

### Phase 3

- move state and ledger storage to PostgreSQL
- add Redis-backed caching and rate limiting
- add richer reporting and visualizations

### Phase 4

- integrate live result fetching
- add scheduling hardening
- improve calibration and evaluation reporting

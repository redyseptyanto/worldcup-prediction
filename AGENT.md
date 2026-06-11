# AGENT.md - World Cup Prediction Baseline

## 1. Purpose

This repository started as documentation-only planning for a World Cup prediction system. The current codebase now implements a baseline vertical slice that future contributors can extend.

The present implementation is deliberately smaller than the original full vision:

- cached real historical data instead of live match ingestion
- file-backed state instead of PostgreSQL
- full 48-team tournament logic, but still with cached rather than live tournament inputs
- working API, simulation, adaptive snapshots, and tests

Treat this repository as a stable baseline, not a finished product.

## 2. Setup

### Prerequisites

- Python 3.13 or newer
- `pip`
- Optional: Docker Desktop for the scaffolded Postgres and Redis services

### Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.data.collector --all --refresh
python -m src.data.loaders --init-db
pytest tests/
```

## 3. Commands

### Make Targets

```bash
make collect-data
make engineer-features
make train-models
make simulate
make predict
make serve-api
make serve-dashboard
make run-all
make ingest-result match_id=GRP-A-M1 score=2-1
make ingest-batch file=path/to/results.csv
make tournament-status
make compare-snapshots from=000_baseline to=001_after_grp-a-m1
make evolution-report
make rollback-to snapshot=000_baseline
make scheduler-run-now
make test
make clean
```

### Direct Python Commands

```bash
python -m src.data.collector --all
python -m src.features.build_features
python -m src.models.train --all
python -m src.simulation.tournament --iterations 500
python -m src.scheduler.daily_run
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
streamlit run src/visualization/dashboard.py
```

## 4. What Exists Today

### Data Layer

- `src/data/collector.py` downloads and caches real historical international results
- `src/data/collector.py` also caches the current 2026 group-stage field, fixture book, weather proxies, and bracket rules
- `src/data/loaders.py` loads fixtures, rankings, and historical matches
- `src/data/preprocessors.py` validates and normalizes CSV inputs

### Feature Layer

- `src/features/history_features.py` builds time-aware training features
- `src/features/team_features.py` computes current team summaries
- `src/features/player_features.py` joins squad ratings, values, injuries, national-team experience, and tactical composition
- `src/features/external_features.py` computes macro, travel, weather, and rest context
- `src/features/build_features.py` writes processed artifacts

### Model Layer

- `src/models/poisson_model.py`
- `src/models/xgboost_model.py`
- `src/models/random_forest_model.py`
- `src/models/elo_model.py`
- `src/models/ensemble.py`

Note:
- the `xgboost_model.py` slot currently uses scikit-learn gradient boosting
- this keeps the model stack lightweight and Python 3.13-friendly
- current seed rankings are derived locally from the downloaded historical results dataset

### Simulation Layer

- `src/simulation/group_stage.py` supports the 12-group 2026 format and best third-placed ranking
- `src/simulation/knockout_stage.py` handles the 32-team knockout bracket
- `src/simulation/tournament.py` produces tournament outputs

### Adaptive Layer

- `src/adaptive/state_machine.py`
- `src/adaptive/ingester.py`
- `src/adaptive/snapshotter.py`
- `src/adaptive/comparer.py`
- `src/adaptive/rollback.py`
- `src/adaptive/engine.py`

### Interfaces

- FastAPI app in `src/api/main.py`
- optional Streamlit dashboard in `src/visualization/dashboard.py`
- scheduler entry point in `src/scheduler/daily_run.py`

## 5. Coding Rules

- Python style: PEP 8
- Type hints: required for public functions
- Keep new code deterministic by default
- Use seeded randomness for simulation code
- Preserve file-backed baseline behavior unless a task explicitly upgrades persistence
- Prefer extending the existing pipeline instead of creating parallel paths

## 6. Documentation Rule

When you change core behavior, update the related docs in the same pass.

Examples:

- Command changes: update `README.md` and `AGENT.md`
- Architecture or scope changes: update `PRD.md`
- New module families: update all three root docs
- New API endpoints: update `README.md`, `AGENT.md`, and `PRD.md`

The test suite includes a basic docs-consistency check. Keep it passing.

## 7. Key Files To Read First

1. `PRD.md`
2. `AGENT.md`
3. [src/config.py](/C:/Users/PSA-Airbyte/autodev/projects/worldcup-prediction/src/config.py:1)
4. [src/models/base.py](/C:/Users/PSA-Airbyte/autodev/projects/worldcup-prediction/src/models/base.py:1)
5. [src/simulation/tournament.py](/C:/Users/PSA-Airbyte/autodev/projects/worldcup-prediction/src/simulation/tournament.py:1)
6. [src/adaptive/engine.py](/C:/Users/PSA-Airbyte/autodev/projects/worldcup-prediction/src/adaptive/engine.py:1)

## 8. Testing

Run:

```bash
pytest tests/
```

Current test coverage focuses on:

- loaders
- feature artifacts
- ensemble output validity
- group-stage simulation
- adaptive ingest behavior
- API smoke checks
- docs consistency

## 9. Known Gaps

- no live match ingestion yet
- no production database integration yet
- no advanced visualization exports yet
- no full scheduler source integration yet

If you extend the project toward those goals, keep the baseline runnable at every step.

# World Cup Prediction Baseline

This repository now contains a working first implementation of the World Cup prediction project described in the original planning docs.

The current build is a local-first baseline:

- It downloads and caches a real historical international results dataset.
- It builds match features from historical results plus multi-source squad, injury, travel, rest, weather, manager, tactical, and macro data.
- It trains a four-part ensemble:
  - Poisson score model
  - Gradient boosting outcome model
  - Random forest outcome model
  - Elo outcome model
- It simulates the current 2026 World Cup structure with 12 groups of 4, best third-placed qualification, and a full round of 32 bracket.
- It supports result ingest, snapshots, comparison, rollback, and a FastAPI surface.

The implementation is intentionally smaller than the original vision. It is honest, runnable, and designed to be extended.

## Current Scope

- Cached real historical data plus the current 2026 World Cup group-stage fixture book
- File-backed state store in `output/state/`
- Snapshot history in `output/snapshots/`
- Prediction ledger in `output/prediction_ledger.csv`
- Optional FastAPI and Streamlit interfaces
- Docker scaffold for future Postgres and Redis work

## Not Implemented Yet

- Live scraping from public football sources
- Real PostgreSQL persistence
- Airflow DAG orchestration
- Production-grade dashboard visual design

## Project Structure

```text
worldcup-prediction/
|- src/
|  |- config.py
|  |- data/
|  |- features/
|  |- models/
|  |- simulation/
|  |- adaptive/
|  |- api/
|  |- scheduler/
|  `- visualization/
|- data/
|  |- raw/
|  |- processed/
|  `- external/
|- docker/
|- tests/
|- AGENT.md
|- PRD.md
|- Makefile
`- requirements.txt
```

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.data.collector --all --refresh
python -m src.data.loaders --init-db
pytest tests/
```

## Main Commands

```bash
make collect-data
make engineer-features
make train-models
make simulate
make predict
make serve-api
make serve-dashboard
make ingest-result match_id=GRP-A-M1 score=2-1
make tournament-status
make scheduler-run-now
make test
```

If `make` is unavailable on your machine, the equivalent Python modules are:

```bash
python -m src.data.collector --all --refresh
python -m src.features.build_features
python -m src.models.train --all
python -m src.simulation.tournament --iterations 500
python -m src.scheduler.daily_run
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
streamlit run src/visualization/dashboard.py
```

## Adaptive Flow

The adaptive engine is file-backed and works like this:

1. Initialize state from fixtures.
2. Run a baseline snapshot.
3. Ingest a resolved result.
4. Re-simulate the remaining tournament.
5. Save an immutable snapshot.
6. Compare or roll back if needed.

Example:

```bash
make ingest-result match_id=GRP-A-M1 score=2-1
make compare-snapshots from=000_baseline to=001_after_grp-a-m1
make rollback-to snapshot=000_baseline
```

## API Endpoints

The implemented API currently exposes:

- `GET /`
- `POST /predict/match`
- `GET /predict/bracket`
- `POST /simulate/run`
- `GET /simulate/results`
- `GET /teams`
- `GET /feature-importance`
- `POST /ingest/result`
- `GET /state/matches`
- `GET /snapshots`

## Testing

The test suite covers:

- real historical data collection and loading
- feature artifact creation
- ensemble probability outputs
- 2026 group-stage simulation behavior
- adaptive ingest and snapshot creation
- API smoke coverage
- docs consistency checks for key repo claims

Run:

```bash
pytest tests/
```

## Next Steps

The most natural extensions from here are:

1. Move state and ledger storage from files to PostgreSQL.
2. Upgrade the dashboard and reporting layer.
3. Add live result fetching with rate-limited source adapters.
4. Extend the knockout-stage travel and weather context beyond the group phase.
5. Improve calibration and post-tournament evaluation reporting.

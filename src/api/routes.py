"""FastAPI routes."""

from __future__ import annotations

from fastapi import APIRouter

from src.adaptive.engine import AdaptiveEngine
from src.adaptive.snapshotter import SnapshotManager
from src.api.schemas import IngestRequest, MatchPredictionRequest, SimulationRequest
from src.models.train import load_or_train_ensemble
from src.simulation.tournament import TournamentSimulator

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "worldcup-prediction-baseline"}


@router.post("/predict/match")
def predict_match(request: MatchPredictionRequest) -> dict[str, object]:
    model = load_or_train_ensemble()
    return model.predict_match(request.home_team, request.away_team)


@router.get("/predict/bracket")
def predict_bracket() -> dict[str, object]:
    simulator = TournamentSimulator(iterations=500)
    return simulator.run()


@router.post("/simulate/run")
def simulate_run(request: SimulationRequest) -> dict[str, object]:
    simulator = TournamentSimulator(iterations=request.iterations)
    return simulator.run()


@router.get("/simulate/results")
def simulate_results() -> dict[str, object]:
    simulator = TournamentSimulator(iterations=250)
    return simulator.run()


@router.get("/teams")
def list_teams() -> list[dict[str, object]]:
    model = load_or_train_ensemble()
    return list(model.team_lookup.values())


@router.get("/feature-importance")
def feature_importance() -> dict[str, object]:
    model = load_or_train_ensemble()
    return model.feature_importance()


@router.post("/ingest/result")
def ingest_result(request: IngestRequest) -> dict[str, object]:
    engine = AdaptiveEngine()
    return engine.ingest_result(request.match_id, request.home_goals, request.away_goals)


@router.get("/state/matches")
def state_matches() -> dict[str, object]:
    engine = AdaptiveEngine()
    return {"matches": engine.state_machine.list_matches()}


@router.get("/snapshots")
def list_snapshots() -> dict[str, object]:
    manager = SnapshotManager()
    return {"snapshots": manager.list_snapshots()}

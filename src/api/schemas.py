"""Pydantic request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MatchPredictionRequest(BaseModel):
    """Payload for a single match prediction request."""

    home_team: str
    away_team: str


class SimulationRequest(BaseModel):
    """Payload for tournament simulation."""

    iterations: int = Field(default=500, ge=10, le=20000)


class IngestRequest(BaseModel):
    """Payload for real result ingestion."""

    match_id: str
    home_goals: int = Field(ge=0, le=15)
    away_goals: int = Field(ge=0, le=15)

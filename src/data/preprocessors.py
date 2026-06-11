"""Validation and preprocessing for raw CSV inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class MatchRecord(BaseModel):
    """Validated historical or fixture match record."""

    match_id: str
    date: str
    stage: str
    group: str | None = None
    home_team: str
    away_team: str
    home_goals: int = Field(ge=0, le=15)
    away_goals: int = Field(ge=0, le=15)
    neutral: bool = True


class FixtureRecord(BaseModel):
    """Validated future fixture record."""

    match_id: str
    date: str
    stage: str
    group: str | None = None
    home_team: str
    away_team: str


@dataclass(frozen=True)
class ValidationSummary:
    """Validation result metadata."""

    rows: int
    errors: int


def validate_matches(records: Iterable[dict[str, object]]) -> ValidationSummary:
    """Validate match dictionaries and raise on first invalid row."""

    errors = 0
    rows = 0
    for record in records:
        rows += 1
        try:
            MatchRecord.model_validate(record)
        except ValidationError:
            errors += 1
            raise
    return ValidationSummary(rows=rows, errors=errors)


def clean_historical_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw match dtypes and ordering."""

    frame = matches.copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    frame["neutral"] = frame["neutral"].astype(bool)
    return frame.sort_values("date").reset_index(drop=True)


def clean_fixtures(fixtures: pd.DataFrame) -> pd.DataFrame:
    """Normalize fixture dtypes and ordering."""

    frame = fixtures.copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.sort_values(["date", "match_id"]).reset_index(drop=True)

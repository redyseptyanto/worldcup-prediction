"""External match and country context features."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

import pandas as pd

from src.config import FIXTURE_CONTEXT_FILE, RAW_FIXTURES_FILE, RAW_MACRO_FILE, RAW_WEATHER_FILE
from src.utils.helpers import save_json


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a_value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_km * math.atan2(math.sqrt(a_value), math.sqrt(1 - a_value))


def build_macro_features() -> pd.DataFrame:
    """Load cached macro indicators for the tournament teams."""

    frame = pd.read_csv(RAW_MACRO_FILE)
    frame["population_total"] = frame["population_total"].fillna(frame["population_total"].median())
    frame["gdp_per_capita"] = frame["gdp_per_capita"].fillna(frame["gdp_per_capita"].median())
    frame["macro_strength"] = (
        0.6 * frame["gdp_per_capita"].rank(pct=True)
        + 0.4 * frame["population_total"].rank(pct=True)
    )
    return frame[["team", "population_total", "gdp_per_capita", "macro_strength"]]


def build_fixture_context() -> dict[str, dict[str, float]]:
    """Build weather, rest, and travel context per fixture."""

    fixtures = pd.read_csv(RAW_FIXTURES_FILE)
    fixtures["date"] = pd.to_datetime(fixtures["date"], utc=True)
    weather = pd.read_csv(RAW_WEATHER_FILE)
    fixtures = fixtures.merge(weather, on="match_id", how="left")

    last_seen: dict[str, dict[str, float | pd.Timestamp]] = defaultdict(dict)
    context: dict[str, dict[str, float]] = {}

    for row in fixtures.sort_values("date").itertuples(index=False):
        home_previous = last_seen.get(row.home_team, {})
        away_previous = last_seen.get(row.away_team, {})

        home_rest_days = float((row.date - home_previous.get("date", row.date)).days)
        away_rest_days = float((row.date - away_previous.get("date", row.date)).days)

        home_travel_km = 0.0
        away_travel_km = 0.0
        if home_previous:
            home_travel_km = _haversine_km(
                float(home_previous["latitude"]),
                float(home_previous["longitude"]),
                float(row.latitude),
                float(row.longitude),
            )
        if away_previous:
            away_travel_km = _haversine_km(
                float(away_previous["latitude"]),
                float(away_previous["longitude"]),
                float(row.latitude),
                float(row.longitude),
            )

        context[row.match_id] = {
            "rest_days_home": home_rest_days,
            "rest_days_away": away_rest_days,
            "rest_days_diff": home_rest_days - away_rest_days,
            "travel_km_home": home_travel_km,
            "travel_km_away": away_travel_km,
            "travel_fatigue_diff": away_travel_km - home_travel_km,
            "weather_temperature": float(row.temperature_2m_mean),
            "weather_precipitation": float(row.precipitation_sum),
            "weather_wind": float(row.wind_speed_10m_max),
        }

        last_seen[row.home_team] = {"date": row.date, "latitude": row.latitude, "longitude": row.longitude}
        last_seen[row.away_team] = {"date": row.date, "latitude": row.latitude, "longitude": row.longitude}

    save_json(Path(FIXTURE_CONTEXT_FILE), context)
    return context

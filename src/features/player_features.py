"""Real player- and squad-level feature engineering."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

import pandas as pd

from src.config import (
    RAW_FIXTURES_FILE,
    RAW_SOFIFA_PLAYERS_FILE,
    RAW_TRANSFERMARKT_INJURIES_FILE,
    RAW_TRANSFERMARKT_NATIONAL_FILE,
    RAW_TRANSFERMARKT_PROFILES_FILE,
    RAW_TRANSFERMARKT_VALUES_FILE,
)

PLAYER_SOURCE_ALIASES = {
    "bosnia herzegovina": "Bosnia and Herzegovina",
    "cabo verde": "Cape Verde",
    "congo dr": "DR Congo",
    "cote d ivoire": "Ivory Coast",
    "curacao": "Curaçao",
    "czechia": "Czech Republic",
    "korea south": "South Korea",
    "korea republic": "South Korea",
    "turkiye": "Turkey",
}


def _normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _normalize_player_name(value: object) -> str:
    normalized = _normalize_text(value)
    return re.sub(r"\b\d+\b$", "", normalized).strip()


def _role_bucket(position_text: str) -> str:
    upper = str(position_text).upper()
    if "GK" in upper:
        return "goalkeeper"
    if any(token in upper for token in ("CB", "LB", "RB", "WB", "DEF")):
        return "defender"
    if any(token in upper for token in ("CDM", "CM", "CAM", "LM", "RM", "MID")):
        return "midfielder"
    return "attacker"


def build_player_factor_features() -> pd.DataFrame:
    """Build real squad, injury, and tactical features from cached raw data."""

    sofifa = pd.read_csv(RAW_SOFIFA_PLAYERS_FILE, low_memory=False)
    profiles = pd.read_csv(RAW_TRANSFERMARKT_PROFILES_FILE, low_memory=False)
    valuations = pd.read_csv(RAW_TRANSFERMARKT_VALUES_FILE)
    injuries = pd.read_csv(RAW_TRANSFERMARKT_INJURIES_FILE)
    national = pd.read_csv(RAW_TRANSFERMARKT_NATIONAL_FILE)
    fixtures = pd.read_csv(RAW_FIXTURES_FILE)
    reference_date = pd.to_datetime(fixtures["date"], utc=True).min()

    sofifa = sofifa.rename(
        columns={
            "long_name": "full_name",
            "overall": "overall_rating",
            "player_positions": "positions",
            "nationality_name": "country_name",
            "value_eur": "value",
        }
    )
    sofifa["name_norm"] = sofifa["full_name"].map(_normalize_player_name)
    sofifa["country_norm"] = sofifa["country_name"].map(_normalize_text).map(
        lambda value: _normalize_text(PLAYER_SOURCE_ALIASES.get(value, value))
    )
    sofifa["dob_date"] = pd.to_datetime(sofifa["dob"], errors="coerce").dt.date
    sofifa["positions_count"] = sofifa["positions"].fillna("").map(lambda value: len([item for item in str(value).split(",") if item.strip()]))
    sofifa["role_bucket"] = sofifa["positions"].fillna("").map(_role_bucket)

    profiles["team"] = profiles["team"].fillna(profiles["citizenship"])
    profiles["name_norm"] = profiles["player_name"].map(_normalize_player_name)
    profiles["home_name_norm"] = profiles["name_in_home_country"].map(_normalize_player_name)
    profiles["date_of_birth"] = pd.to_datetime(profiles["date_of_birth"], errors="coerce").dt.date

    transfermarkt_profiles = profiles[["player_id", "team", "name_norm", "home_name_norm", "main_position", "date_of_birth"]].rename(
        columns={"player_id": "transfermarkt_player_id"}
    )
    direct_team_map = {
        _normalize_text(team_name): team_name
        for team_name in profiles["team"].dropna().unique().tolist()
    }
    sofifa["team_from_country"] = sofifa["country_norm"].map(direct_team_map)
    primary_profiles = transfermarkt_profiles[["transfermarkt_player_id", "team", "name_norm", "main_position", "date_of_birth"]]
    fallback_profiles = transfermarkt_profiles[["transfermarkt_player_id", "team", "home_name_norm", "main_position", "date_of_birth"]].rename(
        columns={"home_name_norm": "name_norm"}
    )
    roster = sofifa.merge(
        primary_profiles,
        left_on=["name_norm", "dob_date"],
        right_on=["name_norm", "date_of_birth"],
        how="left",
    )
    fallback_roster = sofifa.merge(
        fallback_profiles,
        left_on=["name_norm", "dob_date"],
        right_on=["name_norm", "date_of_birth"],
        how="left",
    )
    for column in ("transfermarkt_player_id", "team", "main_position", "date_of_birth"):
        roster[column] = roster[column].fillna(fallback_roster[column])
    roster["team"] = roster["team_from_country"].fillna(roster["team"])
    roster = roster[roster["team"].notna()].copy()
    roster["main_position"] = roster["main_position"].fillna(roster["positions"])

    valuations["date_unix"] = pd.to_datetime(valuations["date_unix"], utc=True, errors="coerce")
    latest_valuations = valuations.sort_values("date_unix").drop_duplicates("player_id", keep="last")
    roster = roster.merge(
        latest_valuations[["player_id", "value"]].rename(
            columns={"player_id": "transfermarkt_player_id", "value": "transfermarkt_value"}
        ),
        on="transfermarkt_player_id",
        how="left",
    )
    roster["transfermarkt_value"] = roster["transfermarkt_value"].fillna(roster["value"].fillna(0))

    injuries["end_date"] = pd.to_datetime(injuries["end_date"], utc=True, errors="coerce")
    injuries["days_missed"] = injuries["days_missed"].fillna(0)
    injuries["games_missed"] = injuries["games_missed"].fillna(0)
    recent_injuries = injuries[injuries["end_date"] >= reference_date - pd.Timedelta(days=365)].copy()
    injury_summary = (
        recent_injuries.groupby("player_id", as_index=False)[["days_missed", "games_missed"]]
        .sum()
        .rename(columns={"days_missed": "recent_days_missed", "games_missed": "recent_games_missed"})
    )
    roster = roster.merge(
        injury_summary.rename(columns={"player_id": "transfermarkt_player_id"}),
        on="transfermarkt_player_id",
        how="left",
    )
    roster["recent_days_missed"] = roster["recent_days_missed"].fillna(0)
    roster["recent_games_missed"] = roster["recent_games_missed"].fillna(0)

    national["matches"] = national["matches"].fillna(0)
    strongest_national_row = national.sort_values(["player_id", "matches"], ascending=[True, False]).drop_duplicates("player_id", keep="first")
    roster = roster.merge(
        strongest_national_row[["player_id", "matches", "coach_id"]].rename(columns={"player_id": "transfermarkt_player_id"}),
        on="transfermarkt_player_id",
        how="left",
    )
    roster["matches"] = roster["matches"].fillna(0)

    feature_rows = []
    for team, squad in roster.groupby("team"):
        squad = squad.sort_values(["overall_rating", "value"], ascending=False).head(26).copy()
        role_counts = Counter(squad["role_bucket"])
        total_players = max(len(squad), 1)
        defenders = role_counts.get("defender", 0) / total_players
        midfielders = role_counts.get("midfielder", 0) / total_players
        attackers = role_counts.get("attacker", 0) / total_players
        goalkeepers = role_counts.get("goalkeeper", 0) / total_players
        tactical_balance = 1.0 - min(
            1.0,
            abs(defenders - 0.35) + abs(midfielders - 0.35) + abs(attackers - 0.22),
        )

        recent_injury_load = float(squad["recent_games_missed"].sum())
        injury_penalty = min(1.0, recent_injury_load / max(total_players * 3, 1))
        availability_score = max(0.0, 1.0 - injury_penalty)

        coach_ids = [int(value) for value in squad["coach_id"].dropna().tolist()]
        if coach_ids:
            continuity = Counter(coach_ids).most_common(1)[0][1] / len(coach_ids)
        else:
            continuity = 0.5

        feature_rows.append(
            {
                "team": team,
                "squad_market_value": float(squad["transfermarkt_value"].fillna(0).sum()),
                "squad_avg_rating": float(squad["overall_rating"].mean()),
                "starting_xi_rating": float(squad.head(11)["overall_rating"].mean()),
                "international_experience": float(squad["matches"].mean()),
                "availability_score": availability_score,
                "injury_load": recent_injury_load,
                "manager_continuity": continuity,
                "tactical_balance": tactical_balance,
                "tactical_defender_share": defenders,
                "tactical_midfielder_share": midfielders,
                "tactical_attacker_share": attackers,
                "goalkeeper_depth": goalkeepers,
                "squad_versatility": float(squad["positions_count"].replace(0, 1).mean()),
            }
        )
    return pd.DataFrame(feature_rows).sort_values("team").reset_index(drop=True)

"""Collect cached real historical and contextual data for predictions."""

from __future__ import annotations

import argparse
import math
import re
import unicodedata
from collections.abc import Iterable
from datetime import date
from difflib import get_close_matches

import pandas as pd
import requests

from src.config import (
    AUTO_RESULTS_FILE,
    RAW_FIXTURES_FILE,
    RAW_MACRO_FILE,
    RAW_MATCHES_FILE,
    RAW_RANKINGS_FILE,
    RAW_SOFIFA_PLAYERS_FILE,
    RAW_THIRD_PLACE_MAPPING_FILE,
    RAW_TRANSFERMARKT_INJURIES_FILE,
    RAW_TRANSFERMARKT_NATIONAL_FILE,
    RAW_TRANSFERMARKT_PROFILES_FILE,
    RAW_TRANSFERMARKT_VALUES_FILE,
    RAW_WEATHER_FILE,
    RAW_XG_MATCHES_FILE,
    ensure_directories,
)
from src.utils.helpers import save_json
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)

REAL_RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
SOFIFA_PLAYERS_URL = "https://raw.githubusercontent.com/ismailoksuz/EAFC26-DataHub/main/data/players.csv"
TRANSFERMARKT_PROFILES_URL = "https://raw.githubusercontent.com/salimt/football-datasets/main/datalake/transfermarkt/player_profiles/player_profiles.csv"
TRANSFERMARKT_VALUES_URL = "https://raw.githubusercontent.com/salimt/football-datasets/main/datalake/transfermarkt/player_latest_market_value/player_latest_market_value.csv"
TRANSFERMARKT_INJURIES_URL = "https://raw.githubusercontent.com/salimt/football-datasets/main/datalake/transfermarkt/player_injuries/player_injuries.csv"
TRANSFERMARKT_NATIONAL_URL = "https://raw.githubusercontent.com/salimt/football-datasets/main/datalake/transfermarkt/player_national_performances/player_national_performances.csv"
WORLD_BANK_COUNTRIES_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
WORLD_BANK_POP_URL = "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json&per_page=20000"
WORLD_BANK_GDP_URL = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?format=json&per_page=20000"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
STATSBOMB_OPEN_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
STATSBOMB_COMPETITIONS_URL = f"{STATSBOMB_OPEN_BASE_URL}/competitions.json"
WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"
FIVETHIRTYEIGHT_INTL_MATCHES_URL = "https://projects.fivethirtyeight.com/soccer-api/international/spi_matches_intl.csv"
FIVETHIRTYEIGHT_INTL_MATCHES_FALLBACK_TIMESTAMP = "20250306125415"
WIKIPEDIA_GROUP_RAW_URL = "https://en.wikipedia.org/w/index.php?title=2026_FIFA_World_Cup_Group_{group_id}&action=raw"
WIKIPEDIA_THIRD_PLACE_RAW_URL = "https://en.wikipedia.org/w/index.php?title=Template:2026_FIFA_World_Cup_third-place_table&action=raw"
WIKI_HEADERS = {"User-Agent": "worldcup-prediction-bot/1.0 (contact@example.com)"}
TRAINING_WINDOW_START = pd.Timestamp("2018-01-01", tz="UTC")
GROUP_IDS = [chr(code) for code in range(ord("A"), ord("L") + 1)]
THIRD_PLACE_SLOT_ORDER = ["A", "B", "D", "E", "G", "I", "K", "L"]
XG_OUTPUT_COLUMNS = [
    "match_id",
    "source_match_id",
    "source",
    "competition",
    "season",
    "date",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "home_xg",
    "away_xg",
]

HOST_COORDINATES = {
    "atlanta": {"city": "Atlanta", "country": "United States", "latitude": 33.7553, "longitude": -84.4008},
    "arlington": {"city": "Arlington", "country": "United States", "latitude": 32.7473, "longitude": -97.0945},
    "boston": {"city": "Foxborough", "country": "United States", "latitude": 42.0909, "longitude": -71.2643},
    "dallas": {"city": "Arlington", "country": "United States", "latitude": 32.7473, "longitude": -97.0945},
    "east rutherford": {"city": "East Rutherford", "country": "United States", "latitude": 40.8135, "longitude": -74.0745},
    "foxborough": {"city": "Foxborough", "country": "United States", "latitude": 42.0909, "longitude": -71.2643},
    "guadalupe": {"city": "Guadalupe", "country": "Mexico", "latitude": 25.6695, "longitude": -100.2442},
    "houston": {"city": "Houston", "country": "United States", "latitude": 29.6847, "longitude": -95.4107},
    "inglewood": {"city": "Inglewood", "country": "United States", "latitude": 33.9535, "longitude": -118.3392},
    "kansas city": {"city": "Kansas City", "country": "United States", "latitude": 39.0489, "longitude": -94.4849},
    "mexico city": {"city": "Mexico City", "country": "Mexico", "latitude": 19.3029, "longitude": -99.1505},
    "miami gardens": {"city": "Miami Gardens", "country": "United States", "latitude": 25.9580, "longitude": -80.2389},
    "philadelphia": {"city": "Philadelphia", "country": "United States", "latitude": 39.9008, "longitude": -75.1675},
    "santa clara": {"city": "Santa Clara", "country": "United States", "latitude": 37.4030, "longitude": -121.9700},
    "seattle": {"city": "Seattle", "country": "United States", "latitude": 47.5952, "longitude": -122.3316},
    "toronto": {"city": "Toronto", "country": "Canada", "latitude": 43.6332, "longitude": -79.4187},
    "vancouver": {"city": "Vancouver", "country": "Canada", "latitude": 49.2768, "longitude": -123.1119},
    "zapopan": {"city": "Zapopan", "country": "Mexico", "latitude": 20.6804, "longitude": -103.4623},
}

TEAM_NAME_ALIASES = {
    "czechia": "Czech Republic",
    "curacao": "Curaçao",
    "cape verde": "Cape Verde",
    "ivory coast": "Ivory Coast",
    "dr congo": "DR Congo",
    "korea republic": "South Korea",
    "south korea": "South Korea",
}

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

WORLD_BANK_NAME_ALIASES = {
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde": "Cabo Verde",
    "Curaçao": "Curacao",
    "Czech Republic": "Czech Republic",
    "DR Congo": "Congo, Dem. Rep.",
    "England": "United Kingdom",
    "Iran": "Iran, Islamic Rep.",
    "Ivory Coast": "Cote d'Ivoire",
    "Scotland": "United Kingdom",
    "South Korea": "Korea, Rep.",
    "United States": "United States",
}


def _normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.text


def _fetch_json(url: str, headers: dict[str, str] | None = None) -> object:
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def _canonical_team_name(name: str) -> str:
    normalized = _normalize_text(name)
    return TEAM_NAME_ALIASES.get(normalized, name)


def _resolve_profile_team(citizenship: object, team_normalized: dict[str, str]) -> str | None:
    raw_value = "" if citizenship is None else str(citizenship)
    parts = [raw_value, *[part for part in re.split(r"\s{2,}|/|;", raw_value) if part.strip()]]
    for part in parts:
        normalized_part = _normalize_text(part)
        canonical_norm = _normalize_text(PLAYER_SOURCE_ALIASES.get(normalized_part, part))
        if canonical_norm in team_normalized:
            return team_normalized[canonical_norm]
    return None


def _parse_timezone_offset(raw_time: str) -> str:
    match = re.search(r"UTC([+\-−]\d{1,2})(?::(\d{2}))?", raw_time)
    if not match:
        return "+00:00"
    hours = match.group(1).replace("−", "-")
    minutes = match.group(2) or "00"
    if len(hours) == 2:
        hours = f"{hours[0]}0{hours[1]}"
    return f"{hours}:{minutes}"


def _parse_match_datetime(section_text: str) -> pd.Timestamp:
    date_match = re.search(r"\|date=\{\{Start date\|(\d{4})\|(\d{1,2})\|(\d{1,2})\}\}", section_text)
    time_match = re.search(r"\|time=([^|\n]+)", section_text)
    if date_match is None or time_match is None:
        raise ValueError("Missing date or time in group fixture section.")

    time_text = time_match.group(1).replace("&nbsp;", " ")
    time_text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", time_text)
    clock_match = re.search(r"(\d{1,2}):(\d{2})\s*([ap])\.m\.", time_text, flags=re.IGNORECASE)
    if clock_match is None:
        raise ValueError(f"Unsupported kickoff time format: {time_text}")

    hour = int(clock_match.group(1))
    minute = int(clock_match.group(2))
    meridiem = clock_match.group(3).lower()
    if meridiem == "p" and hour != 12:
        hour += 12
    if meridiem == "a" and hour == 12:
        hour = 0

    offset = _parse_timezone_offset(time_text)
    timestamp = pd.Timestamp(
        f"{int(date_match.group(1)):04d}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        f"T{hour:02d}:{minute:02d}:00{offset}"
    )
    return timestamp.tz_convert("UTC")


def _parse_stadium_location(section_text: str) -> dict[str, object]:
    stadium_match = re.search(r"\|stadium=([^\n]+)", section_text)
    if stadium_match is None:
        raise ValueError("Missing stadium line in group fixture section.")

    location_text = stadium_match.group(1)
    venue_parts = re.findall(r"\[\[[^\]|]+(?:\|([^\]]+))?\]\]", location_text)
    raw_parts = []
    for match in re.finditer(r"\[\[([^\]]+)\]\]", location_text):
        content = match.group(1)
        raw_parts.append(content.split("|")[-1])
    city_name = raw_parts[-1] if raw_parts else "Unknown"
    city_key = _normalize_text(city_name.split(",")[0])
    if city_key not in HOST_COORDINATES:
        raise KeyError(f"No coordinates configured for host city '{city_name}'.")
    coordinates = HOST_COORDINATES[city_key]
    return {
        "host_city": coordinates["city"],
        "host_country": coordinates["country"],
        "latitude": coordinates["latitude"],
        "longitude": coordinates["longitude"],
    }


def _extract_group_teams(group_raw: str, group_id: str) -> dict[str, str]:
    sentence_match = re.search(r"The group consists of (.*?)\. The top two teams", group_raw, re.S)
    if sentence_match is None:
        raise ValueError(f"Could not parse team sentence for Group {group_id}.")

    team_names = [
        _canonical_team_name(name)
        for name in re.findall(r"\[\[[^\]|]+\|([^\]]+)\]\]", sentence_match.group(1))
    ]
    position_rows = re.findall(
        rf"\|\s*{group_id}([1-4])\s*\|\|[^\n]*?\{{\{{#invoke:flag\|fb\|([A-Z]{{3}})\}}\}}",
        group_raw,
    )
    codes_in_order = [code for _, code in sorted(position_rows, key=lambda item: int(item[0]))]
    if len(team_names) != 4 or len(codes_in_order) != 4:
        raise ValueError(f"Unexpected team metadata in Group {group_id}.")
    return dict(zip(codes_in_order, team_names, strict=True))


def _extract_group_fixtures(group_raw: str, group_id: str) -> list[dict[str, object]]:
    fixtures: list[dict[str, object]] = []
    sections = re.findall(
        rf'<section begin="?{group_id}(\d)"?\s*/>(.*?)<section end="?{group_id}\1"?\s*/>',
        group_raw,
        re.S,
    )
    for section_number, section_text in sections:
        team1_match = re.search(r"\|team1=\{\{#invoke:flag\|fb(?:-rt)?\|([A-Z]{3})\}\}", section_text)
        team2_match = re.search(r"\|team2=\{\{#invoke:flag\|fb\|([A-Z]{3})\}\}", section_text)
        if team1_match is None or team2_match is None:
            raise ValueError(f"Missing team codes in Group {group_id} fixture {section_number}.")
        kickoff_utc = _parse_match_datetime(section_text)
        location = _parse_stadium_location(section_text)
        fixtures.append(
            {
                "match_id": f"GRP-{group_id}-M{section_number}",
                "date": kickoff_utc.isoformat(),
                "stage": "group",
                "round": "group",
                "group": group_id,
                "home_code": team1_match.group(1),
                "away_code": team2_match.group(1),
                **location,
            }
        )
    return sorted(fixtures, key=lambda row: row["match_id"])


def _fetch_actual_tournament() -> tuple[dict[str, str], dict[str, str], pd.DataFrame]:
    all_codes_to_display: dict[str, str] = {}
    group_assignments_by_code: dict[str, str] = {}
    fixture_rows: list[dict[str, object]] = []

    for group_id in GROUP_IDS:
        group_raw = _fetch_text(WIKIPEDIA_GROUP_RAW_URL.format(group_id=group_id), headers=WIKI_HEADERS)
        group_teams = _extract_group_teams(group_raw, group_id)
        all_codes_to_display.update(group_teams)
        for code in group_teams:
            group_assignments_by_code[code] = group_id
        fixture_rows.extend(_extract_group_fixtures(group_raw, group_id))

    fixtures = pd.DataFrame(fixture_rows).sort_values(["date", "match_id"]).reset_index(drop=True)
    return all_codes_to_display, group_assignments_by_code, fixtures


def _parse_third_place_mapping() -> dict[str, dict[str, str]]:
    template_raw = _fetch_text(WIKIPEDIA_THIRD_PLACE_RAW_URL, headers=WIKI_HEADERS)
    mapping: dict[str, dict[str, str]] = {}

    for chunk in template_raw.split("|-"):
        if '! scope="row" |' not in chunk:
            continue
        qualified_groups = tuple(sorted(re.findall(r"'''([A-L])'''", chunk)))
        assignments = re.findall(r"3([A-L])", chunk)
        if len(qualified_groups) == 8 and len(assignments) == 8:
            mapping["|".join(qualified_groups)] = {
                slot: third_group
                for slot, third_group in zip(THIRD_PLACE_SLOT_ORDER, assignments, strict=True)
            }
    if len(mapping) != 495:
        raise ValueError(f"Expected 495 third-place combinations, found {len(mapping)}.")
    return mapping


def _resolve_known_team_name(name: str, known_teams: set[str]) -> str:
    normalized_lookup = {_normalize_text(team): team for team in known_teams}
    normalized_name = _normalize_text(name)
    if normalized_name in normalized_lookup:
        return normalized_lookup[normalized_name]
    close = get_close_matches(normalized_name, list(normalized_lookup), n=1, cutoff=0.75)
    if close:
        return normalized_lookup[close[0]]
    return name


def _statsbomb_competitions_since_2018() -> list[dict[str, object]]:
    competitions = _fetch_json(STATSBOMB_COMPETITIONS_URL)
    selected: list[dict[str, object]] = []
    for row in competitions:
        if not row.get("competition_international") or row.get("competition_gender") != "male":
            continue
        season_name = str(row.get("season_name", ""))
        try:
            season_year = int(season_name[:4])
        except ValueError:
            continue
        if season_year < 2018:
            continue
        selected.append(row)
    return selected


def _statsbomb_match_rows(known_teams: set[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    competitions = _statsbomb_competitions_since_2018()

    for competition in competitions:
        matches_url = (
            f"{STATSBOMB_OPEN_BASE_URL}/matches/"
            f"{competition['competition_id']}/{competition['season_id']}.json"
        )
        matches = _fetch_json(matches_url)
        for match in matches:
            match_id = int(match["match_id"])
            events = _fetch_json(f"{STATSBOMB_OPEN_BASE_URL}/events/{match_id}.json")
            home_name_raw = match["home_team"]["home_team_name"]
            away_name_raw = match["away_team"]["away_team_name"]
            home_team = _resolve_known_team_name(_canonical_team_name(home_name_raw), known_teams)
            away_team = _resolve_known_team_name(_canonical_team_name(away_name_raw), known_teams)

            xg_by_team = {home_name_raw: 0.0, away_name_raw: 0.0}
            for event in events:
                if event.get("type", {}).get("name") != "Shot":
                    continue
                shot = event.get("shot", {})
                team_name = event.get("team", {}).get("name")
                if team_name not in xg_by_team:
                    xg_by_team[team_name] = 0.0
                xg_by_team[team_name] += float(shot.get("statsbomb_xg", 0.0))

            rows.append(
                {
                    "match_id": f"SB-{match_id}",
                    "source_match_id": str(match_id),
                    "source": "statsbomb",
                    "date": pd.Timestamp(match["match_date"], tz="UTC").isoformat(),
                    "competition": competition["competition_name"],
                    "season": competition["season_name"],
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_goals": int(match["home_score"]),
                    "away_goals": int(match["away_score"]),
                    "home_xg": round(float(xg_by_team.get(home_name_raw, 0.0)), 4),
                    "away_xg": round(float(xg_by_team.get(away_name_raw, 0.0)), 4),
                }
            )

    return pd.DataFrame(rows, columns=XG_OUTPUT_COLUMNS).sort_values(["date", "source_match_id"]).reset_index(drop=True)


def _latest_wayback_snapshot_url(target_url: str, fallback_timestamp: str) -> str:
    response = requests.get(
        WAYBACK_CDX_URL,
        params={
            "url": target_url,
            "output": "json",
            "filter": "statuscode:200",
            "fl": "timestamp,original,statuscode,mimetype",
        },
        timeout=60,
    )
    response.raise_for_status()
    rows = response.json()
    if isinstance(rows, list) and len(rows) > 1 and len(rows[-1]) >= 1:
        timestamp = str(rows[-1][0])
    else:
        timestamp = fallback_timestamp
    return f"https://web.archive.org/web/{timestamp}if_/{target_url}"


def _five_thirty_eight_match_rows(known_teams: set[str]) -> pd.DataFrame:
    snapshot_url = _latest_wayback_snapshot_url(
        FIVETHIRTYEIGHT_INTL_MATCHES_URL,
        fallback_timestamp=FIVETHIRTYEIGHT_INTL_MATCHES_FALLBACK_TIMESTAMP,
    )
    matches = pd.read_csv(snapshot_url)
    matches["date"] = pd.to_datetime(matches["date"], utc=True)
    matches = matches[
        (matches["date"] >= TRAINING_WINDOW_START)
        & matches["score1"].notna()
        & matches["score2"].notna()
        & matches["xg1"].notna()
        & matches["xg2"].notna()
    ].copy()

    rows: list[dict[str, object]] = []
    for index, row in enumerate(matches.itertuples(index=False), start=1):
        home_team = _resolve_known_team_name(_canonical_team_name(row.team1), known_teams)
        away_team = _resolve_known_team_name(_canonical_team_name(row.team2), known_teams)
        rows.append(
            {
                "match_id": f"FTE-{index:05d}",
                "source_match_id": f"{int(row.league_id)}-{row.date.strftime('%Y%m%d')}-{index}",
                "source": "five_thirty_eight",
                "competition": row.league,
                "season": str(row.season),
                "date": row.date.isoformat(),
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": int(row.score1),
                "away_goals": int(row.score2),
                "home_xg": round(float(row.xg1), 4),
                "away_xg": round(float(row.xg2), 4),
            }
        )
    return pd.DataFrame(rows, columns=XG_OUTPUT_COLUMNS).sort_values(["date", "source_match_id"]).reset_index(drop=True)


def _merge_xg_sources(frames: list[pd.DataFrame]) -> pd.DataFrame:
    available = [frame.copy() for frame in frames if frame is not None and not frame.empty]
    if not available:
        return pd.DataFrame(columns=XG_OUTPUT_COLUMNS)

    combined = pd.concat(available, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], utc=True)
    combined["source_priority"] = combined["source"].map({"statsbomb": 0, "five_thirty_eight": 1}).fillna(99)
    combined["dedupe_key"] = (
        combined["date"].dt.strftime("%Y-%m-%d")
        + "|"
        + combined["home_team"].astype(str)
        + "|"
        + combined["away_team"].astype(str)
        + "|"
        + combined["home_goals"].astype(str)
        + "|"
        + combined["away_goals"].astype(str)
    )
    combined = combined.sort_values(["source_priority", "date", "match_id", "source_match_id"])
    combined = combined.drop_duplicates(subset="dedupe_key", keep="first")
    combined = combined.drop(columns=["source_priority", "dedupe_key"])
    return combined[XG_OUTPUT_COLUMNS].sort_values(["date", "source", "source_match_id"]).reset_index(drop=True)


def _save_xg_match_data(known_teams: set[str], force_refresh: bool = False) -> None:
    if RAW_XG_MATCHES_FILE.exists() and not force_refresh:
        return

    source_frames: list[pd.DataFrame] = []
    try:
        statsbomb = _statsbomb_match_rows(known_teams)
        source_frames.append(statsbomb)
        LOGGER.info("Collected %s StatsBomb international matches with event-level xG.", len(statsbomb))
    except Exception as exc:  # noqa: BLE001 - keep broader refresh alive if one source is temporarily unavailable.
        LOGGER.warning("Unable to refresh StatsBomb xG data: %s", exc)

    try:
        five_thirty_eight = _five_thirty_eight_match_rows(known_teams)
        source_frames.append(five_thirty_eight)
        LOGGER.info(
            "Collected %s FiveThirtyEight international matches with archived xG coverage.",
            len(five_thirty_eight),
        )
    except Exception as exc:  # noqa: BLE001 - keep higher-quality source if archive lookup fails.
        LOGGER.warning("Unable to refresh FiveThirtyEight archived xG data: %s", exc)

    xg_matches = _merge_xg_sources(source_frames)
    if xg_matches.empty:
        raise RuntimeError("No xG source data could be collected.")
    xg_matches.to_csv(RAW_XG_MATCHES_FILE, index=False)
    source_counts = xg_matches["source"].value_counts().to_dict()
    LOGGER.info(
        "Collected %s historical international matches with real xG coverage after dedupe: %s",
        len(xg_matches),
        source_counts,
    )


def _generate_rankings(historical_matches: pd.DataFrame, tournament_groups: dict[str, str]) -> pd.DataFrame:
    teams = sorted(set(historical_matches["home_team"]) | set(historical_matches["away_team"]) | set(tournament_groups))
    elo = {team: 1500.0 for team in teams}
    appearances = {team: 0 for team in teams}

    for row in historical_matches.sort_values("date").itertuples(index=False):
        expected_home = 1.0 / (1.0 + 10 ** ((elo[row.away_team] - elo[row.home_team]) / 400.0))
        actual_home = 1.0 if row.home_goals > row.away_goals else 0.5 if row.home_goals == row.away_goals else 0.0
        k_factor = 22
        elo[row.home_team] += k_factor * (actual_home - expected_home)
        elo[row.away_team] -= k_factor * (actual_home - expected_home)
        appearances[row.home_team] += 1
        appearances[row.away_team] += 1

    ranking_rows = [
        {
            "team": team,
            "group": tournament_groups.get(team, ""),
            "ranking_points": round(elo[team], 2),
            "seed_rating": round(elo[team], 2),
            "matches_seen": appearances[team],
        }
        for team in teams
    ]
    return pd.DataFrame(ranking_rows).sort_values(["ranking_points", "team"], ascending=[False, True]).reset_index(drop=True)


def _download_real_historical_matches(fixtures: pd.DataFrame) -> pd.DataFrame:
    raw_results = pd.read_csv(REAL_RESULTS_URL, parse_dates=["date"])
    raw_results["date"] = pd.to_datetime(raw_results["date"], utc=True)
    cutoff_date = pd.to_datetime(fixtures["date"], utc=True).min()
    filtered = raw_results[(raw_results["date"] >= TRAINING_WINDOW_START) & (raw_results["date"] < cutoff_date)].copy()
    filtered = filtered.dropna(subset=["home_score", "away_score"])
    filtered = filtered.rename(columns={"home_score": "home_goals", "away_score": "away_goals"})
    filtered["home_goals"] = filtered["home_goals"].astype(int)
    filtered["away_goals"] = filtered["away_goals"].astype(int)
    filtered.insert(0, "match_id", [f"HIST-{index:05d}" for index in range(1, len(filtered) + 1)])
    filtered["stage"] = "historical"
    filtered["group"] = ""
    filtered["round"] = "historical"
    historical_matches = filtered[
        [
            "match_id",
            "date",
            "stage",
            "round",
            "group",
            "home_team",
            "away_team",
            "home_goals",
            "away_goals",
            "tournament",
            "city",
            "country",
            "neutral",
        ]
    ].reset_index(drop=True)
    LOGGER.info(
        "Collected %s real historical international matches from %s through %s.",
        len(historical_matches),
        TRAINING_WINDOW_START.date(),
        (cutoff_date - pd.Timedelta(days=1)).date(),
    )
    return historical_matches


def _save_macro_data(teams: Iterable[str], force_refresh: bool = False) -> None:
    if RAW_MACRO_FILE.exists() and not force_refresh:
        return

    teams = sorted(set(teams))
    countries = requests.get(WORLD_BANK_COUNTRIES_URL, timeout=60).json()[1]
    population_rows = requests.get(WORLD_BANK_POP_URL, timeout=60).json()[1]
    gdp_rows = requests.get(WORLD_BANK_GDP_URL, timeout=60).json()[1]

    country_lookup = {
        _normalize_text(row["name"]): row["id"]
        for row in countries
        if row.get("region", {}).get("value") != "Aggregates"
    }

    def latest_indicator(rows: list[dict[str, object]], country_code: str) -> float | None:
        filtered = [row for row in rows if row.get("countryiso3code") == country_code and row.get("value") is not None]
        if not filtered:
            return None
        filtered.sort(key=lambda row: row["date"], reverse=True)
        return float(filtered[0]["value"])

    macro_rows = []
    normalized_country_names = list(country_lookup)
    for team in teams:
        world_bank_name = WORLD_BANK_NAME_ALIASES.get(team, team)
        normalized_team = _normalize_text(world_bank_name)
        if normalized_team in country_lookup:
            code = country_lookup[normalized_team]
        else:
            close = get_close_matches(normalized_team, normalized_country_names, n=1, cutoff=0.7)
            code = country_lookup[close[0]] if close else ""
        population = latest_indicator(population_rows, code) if code else None
        gdp_per_capita = latest_indicator(gdp_rows, code) if code else None
        macro_rows.append(
            {
                "team": team,
                "world_bank_code": code,
                "population_total": population,
                "gdp_per_capita": gdp_per_capita,
            }
        )
    pd.DataFrame(macro_rows).to_csv(RAW_MACRO_FILE, index=False)


def _download_csv(url: str, path: str, force_refresh: bool = False) -> pd.DataFrame:
    if pd.io.common.file_exists(path) and not force_refresh:
        return pd.read_csv(path, low_memory=False)
    frame = pd.read_csv(url, low_memory=False)
    frame.to_csv(path, index=False)
    return frame


def _save_player_datasets(teams: Iterable[str], force_refresh: bool = False) -> None:
    teams = sorted(set(teams))
    team_normalized = {_normalize_text(team): team for team in teams}

    sofifa = _download_csv(SOFIFA_PLAYERS_URL, str(RAW_SOFIFA_PLAYERS_FILE), force_refresh=force_refresh)
    sofifa.to_csv(RAW_SOFIFA_PLAYERS_FILE, index=False)

    profiles = _download_csv(TRANSFERMARKT_PROFILES_URL, str(RAW_TRANSFERMARKT_PROFILES_FILE), force_refresh=force_refresh)
    profiles["team"] = profiles["citizenship"].map(lambda value: _resolve_profile_team(value, team_normalized))
    profiles = profiles[profiles["team"].notna()].copy()
    profiles["citizenship_norm"] = profiles["citizenship"].map(_normalize_text)
    profiles["name_norm"] = profiles["player_name"].map(_normalize_text)
    profiles["home_name_norm"] = profiles["name_in_home_country"].map(_normalize_text)
    profiles.to_csv(RAW_TRANSFERMARKT_PROFILES_FILE, index=False)

    matched_player_ids = sorted(set(profiles["player_id"]))

    values = _download_csv(TRANSFERMARKT_VALUES_URL, str(RAW_TRANSFERMARKT_VALUES_FILE), force_refresh=force_refresh)
    values = values[values["player_id"].isin(matched_player_ids)].copy()
    values.to_csv(RAW_TRANSFERMARKT_VALUES_FILE, index=False)

    injuries = _download_csv(TRANSFERMARKT_INJURIES_URL, str(RAW_TRANSFERMARKT_INJURIES_FILE), force_refresh=force_refresh)
    injuries = injuries[injuries["player_id"].isin(matched_player_ids)].copy()
    injuries.to_csv(RAW_TRANSFERMARKT_INJURIES_FILE, index=False)

    national = _download_csv(TRANSFERMARKT_NATIONAL_URL, str(RAW_TRANSFERMARKT_NATIONAL_FILE), force_refresh=force_refresh)
    national = national[national["player_id"].isin(matched_player_ids)].copy()
    national.to_csv(RAW_TRANSFERMARKT_NATIONAL_FILE, index=False)


def _weather_proxy_date(match_date: pd.Timestamp) -> date:
    if match_date.year > 2025:
        return date(2025, match_date.month, min(match_date.day, 28 if match_date.month == 2 else match_date.day))
    return match_date.date()


def _save_weather_data(fixtures: pd.DataFrame, force_refresh: bool = False) -> None:
    if RAW_WEATHER_FILE.exists() and not force_refresh:
        return

    rows: list[dict[str, object]] = []
    for row in fixtures.itertuples(index=False):
        match_date = pd.to_datetime(row.date, utc=True)
        proxy_date = _weather_proxy_date(match_date)
        response = requests.get(
            OPEN_METEO_ARCHIVE_URL,
            params={
                "latitude": row.latitude,
                "longitude": row.longitude,
                "start_date": proxy_date.isoformat(),
                "end_date": proxy_date.isoformat(),
                "daily": "temperature_2m_mean,precipitation_sum,wind_speed_10m_max",
                "timezone": "UTC",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()["daily"]
        rows.append(
            {
                "match_id": row.match_id,
                "weather_proxy_date": proxy_date.isoformat(),
                "temperature_2m_mean": payload["temperature_2m_mean"][0],
                "precipitation_sum": payload["precipitation_sum"][0],
                "wind_speed_10m_max": payload["wind_speed_10m_max"][0],
            }
        )
    pd.DataFrame(rows).to_csv(RAW_WEATHER_FILE, index=False)


def _generate_auto_results(fixtures: pd.DataFrame) -> pd.DataFrame:
    first_rows = fixtures.head(2).copy()
    first_rows["home_goals"] = [1, 2]
    first_rows["away_goals"] = [1, 0]
    first_rows["available_at"] = pd.to_datetime(first_rows["date"], utc=True) + pd.Timedelta(hours=3)
    return first_rows[["match_id", "home_goals", "away_goals", "available_at"]]


def collect_all(force_refresh: bool = False) -> None:
    """Collect all raw data required for the enriched prediction pipeline."""

    ensure_directories()

    metadata_missing = any(
        not path.exists()
        for path in (RAW_MATCHES_FILE, RAW_RANKINGS_FILE, RAW_FIXTURES_FILE, RAW_THIRD_PLACE_MAPPING_FILE)
    )

    if force_refresh or metadata_missing:
        display_names_by_code, tournament_groups_by_code, fixture_templates = _fetch_actual_tournament()
        historical_matches = _download_real_historical_matches(fixture_templates)
        known_historical_teams = set(historical_matches["home_team"]) | set(historical_matches["away_team"])
        canonical_names_by_code = {
            code: _resolve_known_team_name(display_name, known_historical_teams)
            for code, display_name in display_names_by_code.items()
        }
        fixtures = fixture_templates.copy()
        fixtures["home_team"] = fixtures["home_code"].map(canonical_names_by_code)
        fixtures["away_team"] = fixtures["away_code"].map(canonical_names_by_code)
        fixtures = fixtures.drop(columns=["home_code", "away_code"])
        tournament_groups = {
            canonical_names_by_code[code]: group_id
            for code, group_id in tournament_groups_by_code.items()
        }
        rankings = _generate_rankings(historical_matches, tournament_groups)
        historical_matches.to_csv(RAW_MATCHES_FILE, index=False)
        rankings.to_csv(RAW_RANKINGS_FILE, index=False)
        fixtures.to_csv(RAW_FIXTURES_FILE, index=False)
        save_json(RAW_THIRD_PLACE_MAPPING_FILE, _parse_third_place_mapping())
    else:
        historical_matches = pd.read_csv(RAW_MATCHES_FILE)
        rankings = pd.read_csv(RAW_RANKINGS_FILE)
        fixtures = pd.read_csv(RAW_FIXTURES_FILE)

    tournament_teams = rankings.loc[rankings["group"].astype(str) != "", "team"].tolist()
    known_teams = set(historical_matches["home_team"]) | set(historical_matches["away_team"]) | set(tournament_teams)
    try:
        _save_xg_match_data(known_teams, force_refresh=force_refresh)
    except Exception as exc:  # noqa: BLE001 - xG is additive; core pipeline should keep working.
        LOGGER.warning("Unable to refresh real xG sidecar data: %s", exc)
    _save_player_datasets(tournament_teams, force_refresh=force_refresh)
    _save_macro_data(tournament_teams, force_refresh=force_refresh)
    _save_weather_data(fixtures, force_refresh=force_refresh)
    auto_results = _generate_auto_results(fixtures)
    auto_results.to_csv(AUTO_RESULTS_FILE, index=False)
    LOGGER.info("Collected cached multi-source prediction inputs.")


def ensure_sample_data() -> None:
    """Create the cached baseline data files if they are missing."""

    required_files = [
        RAW_MATCHES_FILE,
        RAW_RANKINGS_FILE,
        RAW_FIXTURES_FILE,
        RAW_THIRD_PLACE_MAPPING_FILE,
        RAW_SOFIFA_PLAYERS_FILE,
        RAW_TRANSFERMARKT_PROFILES_FILE,
        RAW_TRANSFERMARKT_VALUES_FILE,
        RAW_TRANSFERMARKT_INJURIES_FILE,
        RAW_TRANSFERMARKT_NATIONAL_FILE,
        RAW_MACRO_FILE,
        RAW_WEATHER_FILE,
    ]
    if any(not path.exists() for path in required_files):
        collect_all()


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Collect cached real multi-source football data.")
    parser.add_argument("--all", action="store_true", help="Collect every raw input file.")
    parser.add_argument("--refresh", action="store_true", help="Refresh all remote data sources.")
    args = parser.parse_args()
    collect_all(force_refresh=args.refresh or args.all)


if __name__ == "__main__":
    main()

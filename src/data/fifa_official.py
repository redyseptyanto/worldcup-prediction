"""Official FIFA 2026 tournament data utilities."""

from __future__ import annotations

import argparse
from typing import Any

import httpx
import pandas as pd

from src.config import (
    FIFA_OFFICIAL_BRACKET_FILE,
    FIFA_OFFICIAL_ROUND_OF_32_FILE,
    FIFA_OFFICIAL_STANDINGS_FILE,
    FIFA_OFFICIAL_STANDINGS_RAW_FILE,
    FIFA_OFFICIAL_TEAM_STATS_CATALOG_FILE,
)
from src.utils.helpers import load_json, save_json

FIFA_WORLD_CUP_2026_COMPETITION_ID = "17"
FIFA_WORLD_CUP_2026_SEASON_ID = "285023"
FIFA_WORLD_CUP_2026_GROUP_STAGE_ID = "289273"
FIFA_WORLD_CUP_2026_LANGUAGE = "en"

FIFA_STANDINGS_URL = (
    "https://api.fifa.com/api/v3/calendar/"
    f"{FIFA_WORLD_CUP_2026_COMPETITION_ID}/{FIFA_WORLD_CUP_2026_SEASON_ID}/{FIFA_WORLD_CUP_2026_GROUP_STAGE_ID}"
    f"/standing?language={FIFA_WORLD_CUP_2026_LANGUAGE}&count=200"
)
FIFA_BRACKET_URL = (
    "https://api.fifa.com/api/v3/seasonbracket/season/"
    f"{FIFA_WORLD_CUP_2026_SEASON_ID}?language={FIFA_WORLD_CUP_2026_LANGUAGE}"
)
FIFA_TEAM_STATS_PAGE_URL = (
    "https://cxm-api.fifa.com/fifaplusweb/api/pages/en/tournaments/mens/worldcup/"
    "canadamexicousa2026/statistics/team-statistics"
)

TEAM_NAME_OVERRIDES = {
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "C\u00f4te d'Ivoire": "Ivory Coast",
    "Cura\u00e7ao": "Cura\u00e7ao",
    "Czechia": "Czech Republic",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "T\u00fcrkiye": "Turkey",
    "USA": "United States",
}

_TOURNAMENT_FORM_COLUMNS = [
    "team",
    "official_group",
    "official_group_position",
    "tournament_matches_played",
    "tournament_points_pct",
    "tournament_goal_diff_per_match",
    "tournament_goals_for_per_match",
    "tournament_goals_against_per_match",
    "tournament_wins_per_match",
    "tournament_conduct_score",
    "tournament_qualified",
]


def canonical_team_name(team_name: str) -> str:
    """Normalize official FIFA team names to repo conventions."""

    return TEAM_NAME_OVERRIDES.get(team_name, team_name)


def _client() -> httpx.Client:
    return httpx.Client(timeout=30.0, follow_redirects=True)


def _fetch_json(url: str) -> Any:
    with _client() as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def _parse_standings(payload: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for result in payload.get("Results", []):
        group_label = result.get("Group") or []
        team_info = result.get("Team") or {}
        team_name = ((team_info.get("Name") or [{}])[0]).get("Description", "")
        rows.append(
            {
                "team": canonical_team_name(team_name),
                "team_id": team_info.get("IdTeam"),
                "association_code": team_info.get("IdAssociation"),
                "group": str(((group_label[0] if group_label else {}).get("Description", "")).replace("Group ", "")),
                "position": int(result.get("Position", 0) or 0),
                "played": int(result.get("Played", 0) or 0),
                "won": int(result.get("Won", 0) or 0),
                "drawn": int(result.get("Drawn", 0) or 0),
                "lost": int(result.get("Lost", 0) or 0),
                "goals_for": int(result.get("For", 0) or 0),
                "goals_against": int(result.get("Against", 0) or 0),
                "goal_difference": int(result.get("GoalsDiference", 0) or 0),
                "points": int(result.get("Points", 0) or 0),
                "team_conduct_score": int(result.get("TeamConductScore", 0) or 0),
                "qualification_status": str(result.get("QualificationStatus", "")),
            }
        )
    return pd.DataFrame(rows).sort_values(["group", "position", "team"]).reset_index(drop=True)


def _parse_round_of_32(payload: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    knockout_stages = payload.get("KnockoutStages") or []
    round_of_32 = next(
        (
            stage
            for stage in knockout_stages
            if ((stage.get("Name") or [{}])[0]).get("Description") == "Round of 32"
        ),
        None,
    )
    if round_of_32 is None:
        return pd.DataFrame(
            columns=["annex_c", "match_number", "date", "home_team", "away_team", "home_path", "away_path"]
        )

    for match in round_of_32.get("Matches", []):
        home_team = match.get("HomeTeam") or {}
        away_team = match.get("AwayTeam") or {}
        home_name = canonical_team_name(((home_team.get("TeamName") or [{}])[0]).get("Description", "TBD"))
        away_name = canonical_team_name(((away_team.get("TeamName") or [{}])[0]).get("Description", "TBD"))
        match_number = int(match.get("MatchNumber", 0) or 0)
        rows.append(
            {
                "annex_c": f"M{match_number}",
                "match_number": match_number,
                "date": match.get("Date", ""),
                "home_team": home_name,
                "away_team": away_name,
                "home_path": str(match.get("PlaceHolderA", "")),
                "away_path": str(match.get("PlaceHolderB", "")),
            }
        )
    return pd.DataFrame(rows).sort_values("match_number").reset_index(drop=True)


def _parse_team_stats_catalog(payload: dict[str, Any]) -> dict[str, Any]:
    stats = payload.get("stats") or []
    return {
        "entry_id": payload.get("entryId"),
        "title": payload.get("title"),
        "season_id": payload.get("seasonId"),
        "type": payload.get("type"),
        "view_type": payload.get("viewType"),
        "categories": [
            {
                "entry_id": stat.get("entryId"),
                "title": stat.get("title"),
                "stat_keys": stat.get("stat", []),
                "main_stat": stat.get("mainStat"),
                "display_top_card": bool(stat.get("displayTopCard", False)),
                "glossary": stat.get("glossary", []),
            }
            for stat in stats
        ],
    }


def refresh_official_fifa_data() -> dict[str, str]:
    """Fetch and persist official FIFA standings, bracket, and stat catalog metadata."""

    standings_payload = _fetch_json(FIFA_STANDINGS_URL)
    standings_frame = _parse_standings(standings_payload)
    bracket_payload = _fetch_json(FIFA_BRACKET_URL)
    round_of_32_frame = _parse_round_of_32(bracket_payload)

    team_stats_page = _fetch_json(FIFA_TEAM_STATS_PAGE_URL)
    stats_entry = next(
        (
            section
            for section in team_stats_page.get("sections", [])
            if section.get("entryType") == "sectionTopPerformerGroup"
        ),
        None,
    )
    team_stats_catalog: dict[str, Any] = {}
    if stats_entry and stats_entry.get("entryEndpoint"):
        stats_payload = _fetch_json(f"https://cxm-api.fifa.com/fifaplusweb/api{stats_entry['entryEndpoint']}")
        team_stats_catalog = _parse_team_stats_catalog(stats_payload)

    save_json(FIFA_OFFICIAL_STANDINGS_RAW_FILE, standings_payload)
    standings_frame.to_csv(FIFA_OFFICIAL_STANDINGS_FILE, index=False)
    save_json(FIFA_OFFICIAL_BRACKET_FILE, bracket_payload)
    round_of_32_frame.to_csv(FIFA_OFFICIAL_ROUND_OF_32_FILE, index=False)
    save_json(FIFA_OFFICIAL_TEAM_STATS_CATALOG_FILE, team_stats_catalog)
    return {
        "standings_csv": str(FIFA_OFFICIAL_STANDINGS_FILE),
        "standings_raw_json": str(FIFA_OFFICIAL_STANDINGS_RAW_FILE),
        "bracket_json": str(FIFA_OFFICIAL_BRACKET_FILE),
        "round_of_32_csv": str(FIFA_OFFICIAL_ROUND_OF_32_FILE),
        "team_stats_catalog_json": str(FIFA_OFFICIAL_TEAM_STATS_CATALOG_FILE),
    }


def load_official_standings() -> pd.DataFrame:
    """Load processed official FIFA standings when available."""

    if not FIFA_OFFICIAL_STANDINGS_FILE.exists():
        return pd.DataFrame(
            columns=[
                "team",
                "team_id",
                "association_code",
                "group",
                "position",
                "played",
                "won",
                "drawn",
                "lost",
                "goals_for",
                "goals_against",
                "goal_difference",
                "points",
                "team_conduct_score",
                "qualification_status",
            ]
        )
    return pd.read_csv(FIFA_OFFICIAL_STANDINGS_FILE)


def load_official_round_of_32() -> pd.DataFrame:
    """Load official round-of-32 pairings when available."""

    if not FIFA_OFFICIAL_ROUND_OF_32_FILE.exists():
        return pd.DataFrame(
            columns=["annex_c", "match_number", "date", "home_team", "away_team", "home_path", "away_path"]
        )
    return pd.read_csv(FIFA_OFFICIAL_ROUND_OF_32_FILE)


def build_tournament_form_factors(standings: pd.DataFrame) -> pd.DataFrame:
    """Convert official standings into compact tournament-form features."""

    if standings.empty:
        return pd.DataFrame(columns=_TOURNAMENT_FORM_COLUMNS)

    frame = standings.copy()
    played = frame["played"].clip(lower=1)
    frame["official_group"] = frame["group"]
    frame["official_group_position"] = frame["position"]
    frame["tournament_matches_played"] = frame["played"]
    frame["tournament_points_pct"] = frame["points"] / (played * 3.0)
    frame["tournament_goal_diff_per_match"] = frame["goal_difference"] / played
    frame["tournament_goals_for_per_match"] = frame["goals_for"] / played
    frame["tournament_goals_against_per_match"] = frame["goals_against"] / played
    frame["tournament_wins_per_match"] = frame["won"] / played
    frame["tournament_conduct_score"] = frame["team_conduct_score"]
    frame["tournament_qualified"] = (
        frame["qualification_status"].str.contains("Qualified", case=False, na=False).astype(float)
    )
    return frame[_TOURNAMENT_FORM_COLUMNS].copy()


def load_official_tournament_form() -> pd.DataFrame:
    """Return derived tournament-form factors from the official standings feed."""

    return build_tournament_form_factors(load_official_standings())


def load_official_best_third() -> list[dict[str, Any]]:
    """Return the official qualified third-placed teams when available."""

    standings = load_official_standings()
    if standings.empty:
        return []
    third = standings.loc[standings["position"] == 3].copy()
    third = third.loc[third["qualification_status"].str.contains("Qualified", case=False, na=False)]
    if third.empty:
        return []
    third = third.sort_values(
        ["points", "goal_difference", "goals_for", "team"],
        ascending=[False, False, False, True],
    )
    return [
        {
            "team": row.team,
            "group": row.group,
            "points": int(row.points),
            "goal_difference": int(row.goal_difference),
            "goals_for": int(row.goals_for),
            "goals_against": int(row.goals_against),
            "played": int(row.played),
        }
        for row in third.itertuples(index=False)
    ]


def load_team_stats_catalog() -> dict[str, Any]:
    """Load saved official team-stat category metadata."""

    return load_json(FIFA_OFFICIAL_TEAM_STATS_CATALOG_FILE, default={}) or {}


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Fetch official FIFA 2026 standings and bracket data.")
    parser.add_argument("--refresh", action="store_true", help="Fetch and save the latest official FIFA data.")
    args = parser.parse_args()
    if args.refresh:
        print(refresh_official_fifa_data())
        return
    print(
        {
            "standings_rows": len(load_official_standings()),
            "round_of_32_rows": len(load_official_round_of_32()),
            "team_stat_categories": len((load_team_stats_catalog().get("categories") or [])),
        }
    )


if __name__ == "__main__":
    main()

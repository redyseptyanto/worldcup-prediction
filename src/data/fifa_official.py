"""Official FIFA 2026 tournament data utilities."""

from __future__ import annotations

import argparse
import math
import re
from typing import Any

import httpx
import pandas as pd

from src.config import (
    FIFA_OFFICIAL_BRACKET_FILE,
    FIFA_OFFICIAL_ROUND_OF_32_FILE,
    FIFA_OFFICIAL_STANDINGS_FILE,
    FIFA_OFFICIAL_STANDINGS_RAW_FILE,
    FIFA_OFFICIAL_TEAM_STATS_CATALOG_FILE,
    FIFA_OFFICIAL_TEAM_STATS_FILE,
    FIFA_OFFICIAL_TEAM_STATS_RAW_FILE,
)
from src.utils.helpers import load_json, save_json, utc_timestamp

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
FIFA_GAMEDAY_STORIES_URL = "https://gameday-prod.fifa.mangodev.co.uk/1-0/stories"
FIFA_GAMEDAY_PAGE_LIMIT = 1
FIFA_GAMEDAY_MAX_PAGES = 12
FIFA_GAMEDAY_SORT = "tags.name==urn:gd:tag:story:fifa:column_number:asc"
FIFA_GAMEDAY_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.fifa.com",
    "Referer": "https://www.fifa.com/",
    "User-Agent": "Mozilla/5.0",
}
FIFA_TEAM_STATS_BROWSER_CHANNELS = ("chrome", "msedge")
FIFA_TEAM_STATS_BROWSER_WAIT_MS = 3000

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
_TEAM_STAT_BASE_COLUMNS = ["category", "stat_key", "page_number", "story_id", "team", "rank"]
_TEAM_NAME_KEY_SUFFIXES = (
    "team",
    "team.name",
    "team.shortname",
    "team.displayname",
    "team.title",
    "teamname",
    "team_name",
    "teamtitle",
    "name",
    "title",
    "participant.name",
    "participant.title",
    "participant.displayname",
    "competitor.name",
    "competitor.title",
    "country",
    "country.name",
)
_TEAM_RANK_KEY_SUFFIXES = (
    "rank",
    "ranking",
    "position",
    "standing",
    "tableposition",
)


def canonical_team_name(team_name: str) -> str:
    """Normalize official FIFA team names to repo conventions."""

    return TEAM_NAME_OVERRIDES.get(team_name, team_name)


def _client(*, verify: bool = True) -> httpx.Client:
    return httpx.Client(timeout=30.0, follow_redirects=True, verify=verify)


def _fetch_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    allow_insecure_retry: bool = False,
) -> Any:
    last_error: Exception | None = None
    for verify in ((True, False) if allow_insecure_retry else (True,)):
        try:
            with _client(verify=verify) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type.lower() and not response.text.lstrip().startswith(("{", "[")):
                    raise RuntimeError(f"Expected JSON from {url}, received {content_type or 'unknown content type'}")
                return response.json()
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


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


def _build_team_stats_story_query(stat_key: str, page_number: int) -> str:
    return (
        "(and "
        "resourceStatus==`urn:gd:resourceStatus:active` "
        f"_externalId~`urn:gd:story:classification:{stat_key}:competitionId:{FIFA_WORLD_CUP_2026_SEASON_ID}"
        f":(.*):rank_asc:page:{page_number}$`)"
    )


def _fetch_team_stats_story(stat_key: str, page_number: int) -> dict[str, Any]:
    return _fetch_json(
        FIFA_GAMEDAY_STORIES_URL,
        params={
            "query": _build_team_stats_story_query(stat_key, page_number),
            "skip": 0,
            "limit": FIFA_GAMEDAY_PAGE_LIMIT,
            "sort": FIFA_GAMEDAY_SORT,
        },
        headers=FIFA_GAMEDAY_HEADERS,
        allow_insecure_retry=True,
    )


def _extract_story_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    hits = payload.get("hits")
    if isinstance(hits, dict) and isinstance(hits.get("hits"), list):
        return [item for item in hits["hits"] if isinstance(item, dict)]
    for key in ("items", "results", "stories", "documents"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_story_items(value)
            if nested:
                return nested
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        nested = _extract_story_items(data)
        if nested:
            return nested
    return []


def _flatten_mapping(value: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_prefix = f"{prefix}.{key}" if prefix else str(key)
            flat.update(_flatten_mapping(nested, nested_prefix))
        return flat
    if isinstance(value, list):
        for index, nested in enumerate(value):
            nested_prefix = f"{prefix}.{index}" if prefix else str(index)
            flat.update(_flatten_mapping(nested, nested_prefix))
        return flat
    if prefix:
        flat[prefix] = value
    return flat


def _coerce_rank(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else None
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.isdigit():
            return int(cleaned)
    return None


def _looks_like_team_stat_row(flat_row: dict[str, Any]) -> bool:
    lower_keys = {key.lower() for key in flat_row}
    has_team_key = any(
        key.endswith(suffix) or suffix in key for key in lower_keys for suffix in _TEAM_NAME_KEY_SUFFIXES
    )
    has_rank_key = any(
        key.endswith(suffix) or suffix in key for key in lower_keys for suffix in _TEAM_RANK_KEY_SUFFIXES
    )
    has_numeric_value = any(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in flat_row.values()
    )
    return has_team_key and (has_rank_key or has_numeric_value)


def _extract_team_name_from_flat(flat_row: dict[str, Any]) -> str:
    ranked_keys = sorted(flat_row)
    for suffix in _TEAM_NAME_KEY_SUFFIXES:
        for key in ranked_keys:
            if not key.lower().endswith(suffix) and suffix not in key.lower():
                continue
            value = flat_row[key]
            if isinstance(value, str) and value.strip():
                return canonical_team_name(value.strip())
    return ""


def _extract_rank_from_flat(flat_row: dict[str, Any]) -> int | None:
    ranked_keys = sorted(flat_row)
    for suffix in _TEAM_RANK_KEY_SUFFIXES:
        for key in ranked_keys:
            if not key.lower().endswith(suffix) and suffix not in key.lower():
                continue
            rank = _coerce_rank(flat_row[key])
            if rank is not None:
                return rank
    return None


def _iter_candidate_row_lists(value: Any) -> list[list[dict[str, Any]]]:
    row_lists: list[list[dict[str, Any]]] = []
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            row_lists.append(value)
        for item in value:
            row_lists.extend(_iter_candidate_row_lists(item))
        return row_lists
    if isinstance(value, dict):
        for nested in value.values():
            row_lists.extend(_iter_candidate_row_lists(nested))
    return row_lists


def _parse_team_stats_story_rows(
    payload: dict[str, Any],
    *,
    category: str,
    stat_key: str,
    page_number: int,
) -> list[dict[str, Any]]:
    parsed_rows: list[dict[str, Any]] = []
    story_items = _extract_story_items(payload)
    for story in story_items:
        story_source = story.get("_source") if isinstance(story.get("_source"), dict) else story
        story_id = str(story.get("_id") or story.get("id") or story_source.get("id") or "")
        for row_list in _iter_candidate_row_lists(story_source):
            for raw_row in row_list:
                flat_row = _flatten_mapping(raw_row)
                if not flat_row or not _looks_like_team_stat_row(flat_row):
                    continue
                normalized_row: dict[str, Any] = {
                    "category": category,
                    "stat_key": stat_key,
                    "page_number": page_number,
                    "story_id": story_id,
                    "team": _extract_team_name_from_flat(flat_row),
                    "rank": _extract_rank_from_flat(flat_row),
                }
                for key, value in flat_row.items():
                    if isinstance(value, (dict, list)):
                        continue
                    normalized_row[key] = value
                parsed_rows.append(normalized_row)
    return parsed_rows


def _normalize_team_stat_header(header: str) -> str:
    cleaned = header.strip().lower()
    cleaned = cleaned.replace("%", " pct ")
    cleaned = cleaned.replace("/", " ")
    cleaned = cleaned.replace("-", " ")
    cleaned = re.sub(r"[()\.]", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    if cleaned == "team":
        return "team"
    if cleaned == "rank":
        return "rank"
    return cleaned


def _coerce_team_stat_value(value: str) -> Any:
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return ""
    if cleaned.isdigit():
        return int(cleaned)
    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        return float(cleaned)
    return cleaned


def _normalize_scraped_team_stats_rows(
    *,
    category: str,
    stat_key: str,
    headers: list[str],
    rows: list[list[str]],
) -> list[dict[str, Any]]:
    column_names = [_normalize_team_stat_header(header) for header in headers]
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if len(row) != len(column_names):
            continue
        normalized_row: dict[str, Any] = {
            "category": category,
            "stat_key": stat_key,
            "page_number": 1,
            "story_id": f"browser:{stat_key}",
        }
        for column_name, cell in zip(column_names, row, strict=False):
            normalized_row[column_name] = _coerce_team_stat_value(cell)
        normalized_row["team"] = canonical_team_name(str(normalized_row.get("team", "")).strip())
        normalized_row["rank"] = _coerce_rank(normalized_row.get("rank"))
        normalized_rows.append(normalized_row)
    return normalized_rows


def _empty_team_stats_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=_TEAM_STAT_BASE_COLUMNS)


def _fetch_all_team_stats(catalog: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    category_payloads: list[dict[str, Any]] = []
    warnings: list[str] = []
    normalized_frames: list[pd.DataFrame] = []

    for category in catalog.get("categories", []):
        category_title = str(category.get("title") or "")
        stat_keys = [str(value) for value in category.get("stat_keys", []) if value]
        if not category_title or not stat_keys:
            continue
        stat_key = stat_keys[0]
        pages: list[dict[str, Any]] = []
        page_signatures: set[str] = set()
        for page_number in range(1, FIFA_GAMEDAY_MAX_PAGES + 1):
            try:
                payload = _fetch_team_stats_story(stat_key, page_number)
            except Exception as exc:
                warnings.append(f"{category_title} page {page_number}: {exc}")
                break
            story_items = _extract_story_items(payload)
            if not story_items:
                break
            signature = repr(payload)
            if signature in page_signatures:
                break
            page_signatures.add(signature)
            pages.append({"page_number": page_number, "payload": payload})
            parsed_rows = _parse_team_stats_story_rows(
                payload,
                category=category_title,
                stat_key=stat_key,
                page_number=page_number,
            )
            if parsed_rows:
                normalized_frames.append(pd.DataFrame(parsed_rows))
        category_payloads.append(
            {
                "title": category_title,
                "stat_key": stat_key,
                "pages": pages,
            }
        )

    if normalized_frames:
        stats_frame = pd.concat(normalized_frames, ignore_index=True, sort=False)
        if "team" in stats_frame.columns:
            stats_frame["team"] = stats_frame["team"].fillna("").astype(str)
        if "rank" in stats_frame.columns:
            stats_frame["rank"] = pd.to_numeric(stats_frame["rank"], errors="coerce")
        stats_frame = stats_frame.drop_duplicates().sort_values(
            [column for column in ("category", "page_number", "rank", "team") if column in stats_frame.columns],
            kind="stable",
        )
    else:
        stats_frame = _empty_team_stats_frame()

    raw_payload = {
        "fetched_at": utc_timestamp(),
        "gameday_api_url": FIFA_GAMEDAY_STORIES_URL,
        "season_id": FIFA_WORLD_CUP_2026_SEASON_ID,
        "categories": category_payloads,
        "warnings": warnings,
    }
    return raw_payload, stats_frame.reset_index(drop=True)


def _scrape_team_stats_with_browser(catalog: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    warnings: list[str] = []
    normalized_frames: list[pd.DataFrame] = []

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        warnings.append(f"Playwright import failed: {exc}")
        return {"fetched_at": utc_timestamp(), "method": "browser_scrape", "categories": [], "warnings": warnings}, _empty_team_stats_frame()

    for channel in FIFA_TEAM_STATS_BROWSER_CHANNELS:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel=channel,
                    headless=False,
                    args=["--start-minimized"],
                )
                page = browser.new_page(viewport={"width": 1600, "height": 2200})
                page.goto(
                    "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/statistics/team-statistics",
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                page.wait_for_timeout(10000)

                for button_name in ("I'm OK with that", "Allow All"):
                    consent_button = page.get_by_role("button", name=button_name)
                    if consent_button.count():
                        consent_button.first.click(timeout=5000)
                        page.wait_for_timeout(2000)
                        break

                category_payloads: list[dict[str, Any]] = []
                for category in catalog.get("categories", []):
                    category_title = str(category.get("title") or "")
                    stat_keys = [str(value) for value in category.get("stat_keys", []) if value]
                    if not category_title or not stat_keys:
                        continue
                    stat_key = stat_keys[0]
                    page.get_by_role("button", name=category_title).click(timeout=10000)
                    page.wait_for_timeout(FIFA_TEAM_STATS_BROWSER_WAIT_MS)

                    table = page.locator("table").first
                    row_locator = table.locator("tbody tr")
                    row_count = row_locator.count()
                    if row_count == 0:
                        raise RuntimeError(f"No rendered rows found for {category_title}")

                    headers = [
                        header.inner_text().strip().replace("\n", " ")
                        for header in table.locator("thead th").all()
                    ]
                    raw_rows = [
                        [
                            cell.inner_text().strip().replace("\n", " ")
                            for cell in row.locator("td").all()
                        ]
                        for row in row_locator.all()
                    ]
                    normalized_rows = _normalize_scraped_team_stats_rows(
                        category=category_title,
                        stat_key=stat_key,
                        headers=headers,
                        rows=raw_rows,
                    )
                    if normalized_rows:
                        normalized_frames.append(pd.DataFrame(normalized_rows))
                    category_payloads.append(
                        {
                            "title": category_title,
                            "stat_key": stat_key,
                            "headers": headers,
                            "rows": raw_rows,
                            "row_count": row_count,
                        }
                    )

                stats_frame = (
                    pd.concat(normalized_frames, ignore_index=True, sort=False).drop_duplicates().reset_index(drop=True)
                    if normalized_frames
                    else _empty_team_stats_frame()
                )
                raw_payload = {
                    "fetched_at": utc_timestamp(),
                    "method": "browser_scrape",
                    "browser_channel": channel,
                    "categories": category_payloads,
                    "warnings": warnings,
                }
                browser.close()
                if not stats_frame.empty:
                    return raw_payload, stats_frame
                browser.close()
        except (PlaywrightTimeoutError, RuntimeError, Exception) as exc:
            warnings.append(f"{channel}: {exc}")

    return {
        "fetched_at": utc_timestamp(),
        "method": "browser_scrape",
        "categories": [],
        "warnings": warnings,
    }, _empty_team_stats_frame()


def refresh_official_fifa_data() -> dict[str, str]:
    """Fetch and persist official FIFA standings, bracket, and team statistics."""

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
    team_stats_raw_payload: dict[str, Any] = {"categories": [], "warnings": []}
    team_stats_frame = _empty_team_stats_frame()
    if stats_entry and stats_entry.get("entryEndpoint"):
        stats_payload = _fetch_json(f"https://cxm-api.fifa.com/fifaplusweb/api{stats_entry['entryEndpoint']}")
        team_stats_catalog = _parse_team_stats_catalog(stats_payload)
        api_team_stats_payload, api_team_stats_frame = _fetch_all_team_stats(team_stats_catalog)
        if not api_team_stats_frame.empty:
            team_stats_raw_payload, team_stats_frame = api_team_stats_payload, api_team_stats_frame
        else:
            scraped_team_stats_payload, scraped_team_stats_frame = _scrape_team_stats_with_browser(team_stats_catalog)
            team_stats_raw_payload = {
                **scraped_team_stats_payload,
                "api_fallback": api_team_stats_payload,
            }
            if scraped_team_stats_frame.empty:
                team_stats_raw_payload["warnings"] = [
                    *(api_team_stats_payload.get("warnings") or []),
                    *(scraped_team_stats_payload.get("warnings") or []),
                ]
            team_stats_frame = scraped_team_stats_frame

    save_json(FIFA_OFFICIAL_STANDINGS_RAW_FILE, standings_payload)
    standings_frame.to_csv(FIFA_OFFICIAL_STANDINGS_FILE, index=False)
    save_json(FIFA_OFFICIAL_BRACKET_FILE, bracket_payload)
    round_of_32_frame.to_csv(FIFA_OFFICIAL_ROUND_OF_32_FILE, index=False)
    save_json(FIFA_OFFICIAL_TEAM_STATS_CATALOG_FILE, team_stats_catalog)
    save_json(FIFA_OFFICIAL_TEAM_STATS_RAW_FILE, team_stats_raw_payload)
    team_stats_frame.to_csv(FIFA_OFFICIAL_TEAM_STATS_FILE, index=False)
    result = {
        "standings_csv": str(FIFA_OFFICIAL_STANDINGS_FILE),
        "standings_raw_json": str(FIFA_OFFICIAL_STANDINGS_RAW_FILE),
        "bracket_json": str(FIFA_OFFICIAL_BRACKET_FILE),
        "round_of_32_csv": str(FIFA_OFFICIAL_ROUND_OF_32_FILE),
        "team_stats_catalog_json": str(FIFA_OFFICIAL_TEAM_STATS_CATALOG_FILE),
        "team_stats_raw_json": str(FIFA_OFFICIAL_TEAM_STATS_RAW_FILE),
        "team_stats_csv": str(FIFA_OFFICIAL_TEAM_STATS_FILE),
    }
    warnings = team_stats_raw_payload.get("warnings") or []
    if warnings and team_stats_frame.empty:
        result["team_stats_warning"] = f"{len(warnings)} warning(s); inspect raw JSON for details"
    return result


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


def load_official_team_stats() -> pd.DataFrame:
    """Load normalized official FIFA team statistics when available."""

    if not FIFA_OFFICIAL_TEAM_STATS_FILE.exists():
        return _empty_team_stats_frame()
    return pd.read_csv(FIFA_OFFICIAL_TEAM_STATS_FILE)


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
            "team_stat_rows": len(load_official_team_stats()),
        }
    )


if __name__ == "__main__":
    main()

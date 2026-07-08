from src.data.fifa_official import (
    _extract_completed_round_of_16_results,
    _extract_completed_round_of_32_results,
    _build_team_stats_story_query,
    _extract_story_items,
    _normalize_scraped_team_stats_rows,
    _parse_team_stats_story_rows,
)


def test_build_team_stats_story_query_matches_fifa_pattern() -> None:
    query = _build_team_stats_story_query("gct_attack", 3)

    assert "resourceStatus==`urn:gd:resourceStatus:active`" in query
    assert "classification:gct_attack" in query
    assert "competitionId:285023" in query
    assert "page:3$" in query


def test_extract_story_items_supports_hits_payload() -> None:
    payload = {
        "hits": {
            "hits": [
                {"_id": "story-1", "_source": {"rows": []}},
                {"_id": "story-2", "_source": {"rows": []}},
            ]
        }
    }

    items = _extract_story_items(payload)

    assert len(items) == 2
    assert items[0]["_id"] == "story-1"


def test_parse_team_stats_story_rows_flattens_nested_team_rows() -> None:
    payload = {
        "hits": {
            "hits": [
                {
                    "_id": "story-attack-1",
                    "_source": {
                        "table": {
                            "rows": [
                                {
                                    "rank": 1,
                                    "team": {"name": "Brazil"},
                                    "stats": {"goals": 10, "xg": 8.4},
                                },
                                {
                                    "position": "2",
                                    "teamName": "USA",
                                    "stats": {"goals": 8, "attemptsOnTarget": 21},
                                },
                            ]
                        }
                    },
                }
            ]
        }
    }

    rows = _parse_team_stats_story_rows(
        payload,
        category="Attacking",
        stat_key="gct_attack",
        page_number=1,
    )

    assert len(rows) == 2
    assert rows[0]["category"] == "Attacking"
    assert rows[0]["team"] == "Brazil"
    assert rows[0]["rank"] == 1
    assert rows[0]["stats.goals"] == 10
    assert rows[1]["team"] == "United States"
    assert rows[1]["rank"] == 2
    assert rows[1]["stats.attemptsOnTarget"] == 21


def test_normalize_scraped_team_stats_rows_maps_headers_and_team_overrides() -> None:
    rows = _normalize_scraped_team_stats_rows(
        category="Physical",
        stat_key="gct_physical",
        headers=["Rank", "Team", "Average Speed (km/h)", "xG Efficiency", "Total Distance (m)"],
        rows=[["4", "USA", "6.23", "1.53x", "358610.48"]],
    )

    assert len(rows) == 1
    assert rows[0]["team"] == "United States"
    assert rows[0]["rank"] == 4
    assert rows[0]["average_speed_km_h"] == 6.23
    assert rows[0]["xg_efficiency"] == "1.53x"
    assert rows[0]["total_distance_m"] == 358610.48


def test_extract_completed_round_of_32_results_tracks_penalty_winners() -> None:
    payload = {
        "KnockoutStages": [
            {
                "Name": [{"Description": "Round of 32"}],
                "Matches": [
                    {
                        "MatchStatus": 0,
                        "MatchNumber": 74,
                        "Date": "2026-06-29T20:30:00Z",
                        "Winner": "away-id",
                        "HomeTeam": {
                            "IdTeam": "home-id",
                            "Score": 1,
                            "TeamName": [{"Description": "Germany"}],
                        },
                        "AwayTeam": {
                            "IdTeam": "away-id",
                            "Score": 1,
                            "TeamName": [{"Description": "Paraguay"}],
                        },
                    }
                ],
            }
        ]
    }

    rows = _extract_completed_round_of_32_results(payload)

    assert len(rows) == 1
    assert rows[0]["match_id"] == "R32-2"
    assert rows[0]["winner"] == "Paraguay"
    assert rows[0]["advancement_method"] == "penalties"


def test_extract_completed_round_of_16_results_tracks_penalty_winners() -> None:
    payload = {
        "KnockoutStages": [
            {
                "Name": [{"Description": "Round of 16"}],
                "Matches": [
                    {
                        "MatchStatus": 0,
                        "MatchNumber": 96,
                        "Date": "2026-07-08T02:00:00Z",
                        "Winner": "home-id",
                        "HomeTeam": {
                            "IdTeam": "home-id",
                            "Score": 0,
                            "TeamName": [{"Description": "Switzerland"}],
                        },
                        "AwayTeam": {
                            "IdTeam": "away-id",
                            "Score": 0,
                            "TeamName": [{"Description": "Colombia"}],
                        },
                    }
                ],
            }
        ]
    }

    rows = _extract_completed_round_of_16_results(payload)

    assert len(rows) == 1
    assert rows[0]["match_id"] == "R16-8"
    assert rows[0]["winner"] == "Switzerland"
    assert rows[0]["advancement_method"] == "penalties"

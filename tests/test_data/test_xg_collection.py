import pandas as pd

from src.data.collector import _merge_xg_sources


def test_merge_xg_sources_prefers_statsbomb_on_overlap() -> None:
    statsbomb = pd.DataFrame(
        [
            {
                "match_id": "SB-1",
                "source_match_id": "1",
                "source": "statsbomb",
                "competition": "FIFA World Cup",
                "season": "2022",
                "date": "2022-11-22T00:00:00+00:00",
                "home_team": "Argentina",
                "away_team": "Saudi Arabia",
                "home_goals": 1,
                "away_goals": 2,
                "home_xg": 2.3,
                "away_xg": 0.1,
            }
        ]
    )
    five_thirty_eight = pd.DataFrame(
        [
            {
                "match_id": "FTE-1",
                "source_match_id": "wc-1",
                "source": "five_thirty_eight",
                "competition": "FIFA World Cup",
                "season": "2022",
                "date": "2022-11-22T00:00:00+00:00",
                "home_team": "Argentina",
                "away_team": "Saudi Arabia",
                "home_goals": 1,
                "away_goals": 2,
                "home_xg": 1.9,
                "away_xg": 0.4,
            },
            {
                "match_id": "FTE-2",
                "source_match_id": "fr-1",
                "source": "five_thirty_eight",
                "competition": "International Match",
                "season": "2024",
                "date": "2024-03-22T00:00:00+00:00",
                "home_team": "France",
                "away_team": "Germany",
                "home_goals": 0,
                "away_goals": 2,
                "home_xg": 1.1,
                "away_xg": 1.5,
            },
        ]
    )

    merged = _merge_xg_sources([statsbomb, five_thirty_eight])

    assert len(merged) == 2
    overlap = merged[(merged["home_team"] == "Argentina") & (merged["away_team"] == "Saudi Arabia")].iloc[0]
    assert overlap["source"] == "statsbomb"
    assert overlap["home_xg"] == 2.3
    france_match = merged[(merged["home_team"] == "France") & (merged["away_team"] == "Germany")].iloc[0]
    assert france_match["source"] == "five_thirty_eight"

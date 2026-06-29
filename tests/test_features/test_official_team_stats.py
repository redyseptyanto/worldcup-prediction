import pandas as pd

from src.features.official_team_stats import build_official_team_stats_features


def test_build_official_team_stats_features_creates_compact_recent_form_indices() -> None:
    team_stats = pd.DataFrame(
        [
            {
                "team": "France",
                "rank": 1,
                "goals": 10,
                "xg": 6.0,
                "attempts_on_target": 22,
                "attempts_at_goal_conv_rate_pct": 21,
                "attempts_inside_the_penalty_area": 28,
                "passes": 1800,
                "passing_accuracy_pct": 90,
                "defensive_linebreaks_attempted": 70,
                "defensive_linebreaks_acc_pct": 61,
                "switches_of_play_acc_pct": 82,
                "goals_conceded": 2,
                "forced_turnovers": 150,
                "ball_recovery_time_s": 41,
                "defensive_pressures_applied": 760,
                "defensive_pressures_directly_applied": 150,
                "clean_sheets": 2,
                "goalkeeper_save_percentage_pct": 76,
                "goalkeeper_actions_outside_the_penalty_area": 25,
                "yellow_cards": 2,
                "red_cards": 0,
                "indirect_red_cards": 0,
                "fouls_against": 24,
                "offsides": 5,
                "offers_to_receive": 1200,
                "offers_in_behind": 330,
                "offers_in_between": 420,
                "receptions_in_behind": 41,
                "receptions_between_midfield_and_defensive_line": 300,
                "receptions_under_pressure": 600,
                "average_speed_km_h": 6.1,
                "high_speed_running": 3900,
                "sprints": 1400,
                "total_distance_m": 340000,
                "xg_efficiency": "1.67x",
            },
            {
                "team": "Australia",
                "rank": 20,
                "goals": 3,
                "xg": 2.2,
                "attempts_on_target": 8,
                "attempts_at_goal_conv_rate_pct": 10,
                "attempts_inside_the_penalty_area": 12,
                "passes": 1100,
                "passing_accuracy_pct": 76,
                "defensive_linebreaks_attempted": 25,
                "defensive_linebreaks_acc_pct": 35,
                "switches_of_play_acc_pct": 55,
                "goals_conceded": 7,
                "forced_turnovers": 80,
                "ball_recovery_time_s": 67,
                "defensive_pressures_applied": 500,
                "defensive_pressures_directly_applied": 90,
                "clean_sheets": 0,
                "goalkeeper_save_percentage_pct": 52,
                "goalkeeper_actions_outside_the_penalty_area": 11,
                "yellow_cards": 6,
                "red_cards": 1,
                "indirect_red_cards": 0,
                "fouls_against": 40,
                "offsides": 11,
                "offers_to_receive": 850,
                "offers_in_behind": 140,
                "offers_in_between": 180,
                "receptions_in_behind": 14,
                "receptions_between_midfield_and_defensive_line": 180,
                "receptions_under_pressure": 330,
                "average_speed_km_h": 5.8,
                "high_speed_running": 3200,
                "sprints": 1180,
                "total_distance_m": 312000,
                "xg_efficiency": "0.91x",
            },
        ]
    )
    tournament_form = pd.DataFrame(
        [
            {
                "team": "France",
                "tournament_matches_played": 3,
                "tournament_points_pct": 1.0,
                "tournament_goal_diff_per_match": 2.0,
                "tournament_wins_per_match": 1.0,
            },
            {
                "team": "Australia",
                "tournament_matches_played": 3,
                "tournament_points_pct": 0.0,
                "tournament_goal_diff_per_match": -1.5,
                "tournament_wins_per_match": 0.0,
            },
        ]
    )

    features = build_official_team_stats_features(team_stats, tournament_form=tournament_form)

    assert set(features["team"]) == {"France", "Australia"}
    france = features.loc[features["team"] == "France"].iloc[0]
    australia = features.loc[features["team"] == "Australia"].iloc[0]
    assert france["official_stats_weight"] == 0.3
    assert france["official_recent_form_index"] > australia["official_recent_form_index"]
    assert france["official_attack_signal"] > australia["official_attack_signal"]
    assert france["official_defense_signal"] > australia["official_defense_signal"]

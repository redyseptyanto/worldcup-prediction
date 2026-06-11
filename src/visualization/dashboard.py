"""Streamlit dashboard entry point."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.visualization.accuracy_charts import accuracy_summary
from src.visualization.bracket import load_latest_bracket
from src.visualization.evolution_timeline import list_snapshot_timeline
from src.visualization.probability_heatmap import probability_table
from src.visualization.standings import load_latest_standings

FLAG_BY_TEAM = {
    "Argentina": "🇦🇷",
    "Brazil": "🇧🇷",
    "France": "🇫🇷",
    "Japan": "🇯🇵",
    "Mexico": "🇲🇽",
    "United States": "🇺🇸",
}


def _inject_styles(st: Any) -> None:
    """Apply a clean tournament-board style to the dashboard."""

    st.markdown(
        """
        <style>
        .stApp {
            background: #ffffff;
            color: #10231f;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }
        .overview-shell {
            background: transparent;
        }
        .overview-title {
            font-size: 2.35rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
            color: #0f3d35;
        }
        .overview-subtitle {
            color: #4b635d;
            font-size: 1rem;
            margin-bottom: 1.4rem;
        }
        .group-card {
            border: 1px solid #d5e4df;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 14px 28px rgba(15, 61, 53, 0.08);
            background: #ffffff;
            margin-bottom: 1rem;
        }
        .group-card-header {
            background: #123f37;
            color: #ffffff;
            padding: 0.7rem 1rem;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .group-table {
            width: 100%;
            border-collapse: collapse;
        }
        .group-table th {
            text-align: left;
            padding: 0.6rem 0.75rem;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #5a726b;
            border-bottom: 1px solid #e6efec;
            background: #f7fbf9;
        }
        .group-table td {
            padding: 0.62rem 0.75rem;
            font-size: 0.92rem;
            border-bottom: 1px solid #edf3f1;
        }
        .group-table tr:last-child td {
            border-bottom: none;
        }
        .qualified-row {
            background: #eff9f4;
            font-weight: 700;
        }
        .team-cell {
            white-space: nowrap;
        }
        .qual-pill {
            display: inline-block;
            margin-left: 0.45rem;
            padding: 0.16rem 0.42rem;
            border-radius: 999px;
            background: #1f8f6a;
            color: #ffffff;
            font-size: 0.67rem;
            font-weight: 700;
            vertical-align: middle;
        }
        .knockout-shell {
            margin-top: 1.25rem;
            border: 1px solid #d5e4df;
            border-radius: 20px;
            padding: 1.2rem 1.2rem 0.8rem;
            box-shadow: 0 14px 28px rgba(15, 61, 53, 0.08);
            background: #ffffff;
        }
        .knockout-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: #123f37;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .match-card {
            border: 1px solid #dce8e4;
            border-radius: 16px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.85rem;
            background: #fcfefd;
        }
        .match-round {
            color: #6f857f;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.7rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
        }
        .match-line {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            padding: 0.22rem 0;
            font-size: 0.96rem;
        }
        .match-team {
            font-weight: 700;
            color: #10231f;
        }
        .match-meta {
            font-size: 0.78rem;
            color: #5f756f;
        }
        .winner-mark {
            color: #1f8f6a;
            font-weight: 800;
            margin-left: 0.35rem;
        }
        .champion-card {
            border: 1px solid #dce8e4;
            border-radius: 22px;
            background: linear-gradient(180deg, #fffdf5 0%, #ffffff 100%);
            padding: 1.35rem 1rem;
            text-align: center;
            min-height: 100%;
        }
        .champion-trophy {
            font-size: 3rem;
            line-height: 1;
            margin-bottom: 0.65rem;
        }
        .champion-label {
            color: #7b6a2d;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.72rem;
            font-weight: 800;
        }
        .champion-team {
            margin-top: 0.4rem;
            font-size: 1.25rem;
            font-weight: 800;
            color: #10231f;
        }
        .champion-odds {
            margin-top: 0.3rem;
            color: #556b65;
            font-size: 0.9rem;
        }
        .snapshots-note {
            color: #5d736d;
            font-size: 0.9rem;
            margin-top: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _flag(team: str) -> str:
    """Return a best-effort flag icon for the known teams."""

    return FLAG_BY_TEAM.get(team, "🏳️")


def _sorted_group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure qualified teams remain on top of the group table."""

    enriched = []
    for index, row in enumerate(rows):
        enriched.append({**row, "qualified": index < 2})
    return sorted(
        enriched,
        key=lambda row: (
            0 if row["qualified"] else 1,
            -row["points"],
            -row["goal_difference"],
            -row["goals_for"],
            row["team"],
        ),
    )


def _render_group_card(st: Any, group_id: str, rows: list[dict[str, Any]]) -> None:
    """Render one group standings card."""

    ordered_rows = _sorted_group_rows(rows)
    table_rows = []
    for position, row in enumerate(ordered_rows, start=1):
        qualifier = '<span class="qual-pill">Q</span>' if row["qualified"] else ""
        row_class = "qualified-row" if row["qualified"] else ""
        table_rows.append(
            f"""
            <tr class="{row_class}">
                <td>{position}</td>
                <td class="team-cell">{_flag(row['team'])} {row['team']}{qualifier}</td>
                <td>{row['points']}</td>
                <td>{row['goal_difference']}</td>
                <td>{row['goals_for']}</td>
            </tr>
            """
        )
    st.markdown(
        f"""
        <div class="group-card">
            <div class="group-card-header">Group {group_id}</div>
            <table class="group-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Team</th>
                        <th>Pts</th>
                        <th>GD</th>
                        <th>GF</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_match_card(st: Any, round_label: str, match: dict[str, Any]) -> None:
    """Render a knockout match card."""

    prediction = match.get("prediction", {})
    score = match.get("score", {})
    winner = match.get("winner", "")
    probability = max(prediction.get("outcome_probabilities", {}).values(), default=0.0)

    def team_line(team: str, goals: Any) -> str:
        winner_mark = '<span class="winner-mark">Qualified</span>' if team == winner else ""
        return (
            f'<div class="match-line">'
            f'<span class="match-team">{_flag(team)} {team}{winner_mark}</span>'
            f'<span>{goals}</span>'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="match-card">
            <div class="match-round">{round_label}</div>
            {team_line(match['home_team'], score.get('home', '-'))}
            {team_line(match['away_team'], score.get('away', '-'))}
            <div class="match-meta">
                Predicted score {prediction.get('predicted_score', {}).get('home', '-')}
                -
                {prediction.get('predicted_score', {}).get('away', '-')}
                | confidence {prediction.get('confidence', {}).get('overall', 0):.1f}
                | top win probability {probability:.1%}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_overview(st: Any) -> None:
    """Render the tournament-board overview."""

    standings = load_latest_standings()
    bracket_data = load_latest_bracket()
    snapshots = list_snapshot_timeline()
    champion_odds = bracket_data.get("champion_odds", {})
    bracket = bracket_data.get("bracket", {})
    semi_finals = bracket.get("semi_finals", [])
    final_match = bracket.get("final")
    champion = max(champion_odds, key=champion_odds.get) if champion_odds else None

    st.markdown(
        """
        <div class="overview-shell">
            <div class="overview-title">Tournament Overview</div>
            <div class="overview-subtitle">
                Group leaders and qualifiers at the top, knockout path underneath.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if standings:
        groups = sorted(standings.items())
        for row_start in range(0, len(groups), 4):
            columns = st.columns(4)
            for column, (group_id, rows) in zip(columns, groups[row_start : row_start + 4]):
                with column:
                    _render_group_card(st, group_id, rows)
    else:
        st.info("No standings snapshot is available yet.")

    st.markdown('<div class="knockout-shell"><div class="knockout-title">Knockout Picture</div></div>', unsafe_allow_html=True)
    left_col, center_col, right_col = st.columns([1.25, 0.9, 1.25])

    with left_col:
        if semi_finals:
            _render_match_card(st, "Semi-final 1", semi_finals[0])
        else:
            st.info("No semi-final projection available.")

    with center_col:
        champion_flag = _flag(champion) if champion else "🏆"
        champion_probability = champion_odds.get(champion, 0.0) if champion else 0.0
        st.markdown(
            f"""
            <div class="champion-card">
                <div class="champion-trophy">{champion_flag if champion else "🏆"}</div>
                <div class="champion-label">Projected Champion</div>
                <div class="champion-team">{champion_flag} {champion if champion else "TBD"}</div>
                <div class="champion-odds">{champion_probability:.1%} title probability</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if final_match:
            _render_match_card(st, "Final", final_match)

    with right_col:
        if len(semi_finals) > 1:
            _render_match_card(st, "Semi-final 2", semi_finals[1])
        else:
            st.info("No second semi-final projection available.")

    if snapshots:
        st.markdown(
            f'<div class="snapshots-note">Snapshots loaded: {", ".join(snapshots)}</div>',
            unsafe_allow_html=True,
        )


def main() -> None:
    """Launch the optional Streamlit dashboard if available."""

    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise SystemExit("Streamlit is not installed. Install requirements to use the dashboard.") from exc

    st.set_page_config(page_title="World Cup Prediction Baseline", layout="wide")
    _inject_styles(st)
    st.title("World Cup Prediction Baseline")
    st.caption("Offline demo pipeline with adaptive snapshots.")

    overview, standings_tab, predictions_tab, accuracy_tab, compare_tab = st.tabs(
        ["Overview", "Standings", "Predictions", "Accuracy", "Compare"]
    )

    with overview:
        _render_overview(st)

    with standings_tab:
        st.subheader("Current Group Standings")
        standings = load_latest_standings()
        if standings:
            for group_id, rows in sorted(standings.items()):
                st.markdown(f"### Group {group_id}")
                frame = pd.DataFrame(_sorted_group_rows(rows))
                frame["team"] = frame.apply(
                    lambda row: f"{_flag(row['team'])} {row['team']}" + ("  QUALIFIED" if row["qualified"] else ""),
                    axis=1,
                )
                st.dataframe(
                    frame[["team", "points", "goal_difference", "goals_for", "goals_against", "played"]],
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("No standings snapshot is available yet.")

    with predictions_tab:
        st.subheader("Match Predictions")
        table = probability_table()
        if table:
            frame = pd.DataFrame(table)
            for column in ("home_team", "away_team"):
                frame[column] = frame[column].map(lambda team: f"{_flag(team)} {team}")
            st.dataframe(frame, use_container_width=True, hide_index=True)
        else:
            st.info("Prediction outputs have not been generated yet.")

    with accuracy_tab:
        st.subheader("Prediction Ledger Summary")
        st.json(accuracy_summary())

    with compare_tab:
        st.write("Use the API or CLI compare command to generate detailed snapshot comparisons.")


if __name__ == "__main__":
    main()

"""Streamlit dashboard entry point."""

from __future__ import annotations

from typing import Any

import base64
import pandas as pd
import sys
from pathlib import Path

# Ensure the root directory is in sys.path so 'src' can be imported
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config import ENSEMBLE_MODEL_FILE, FLAGS_DIR
from src.models.train import current_model_metadata
from src.utils.helpers import load_json

def _render_html(st, html_str: str) -> None:
    import re
    st.markdown(re.sub(r'\n\s+', '\n', html_str), unsafe_allow_html=True)

from src.visualization.accuracy_charts import accuracy_summary
from src.visualization.bracket import load_latest_bracket
from src.visualization.evolution_timeline import list_snapshot_timeline
from src.visualization.head_to_head import get_head_to_head
from src.visualization.probability_heatmap import probability_table
from src.visualization.snapshot_store import load_snapshot_file
from src.visualization.standings import load_latest_standings


def _ensure_baseline_snapshot() -> None:
    """Create a baseline snapshot when the dashboard has nothing to render."""

    from src.adaptive.engine import AdaptiveEngine

    AdaptiveEngine(iterations=500).create_baseline_snapshot()


def _refresh_snapshot(snapshot_id: str) -> None:
    """Recompute one stored snapshot using the current trained model artifacts."""

    from src.adaptive.engine import AdaptiveEngine

    AdaptiveEngine(iterations=500).refresh_snapshot(snapshot_id)


def _snapshot_label(snapshot: dict[str, Any]) -> str:
    model_signature = ((snapshot.get("model_metadata") or {}).get("signature")) or "unknown"
    resolved_count = len(snapshot.get("resolved_matches", []))
    return f"{snapshot['snapshot_id']} | {snapshot['descriptor']} | resolved {resolved_count} | model {model_signature}"


def _find_snapshot(snapshot_id: str, snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((snapshot for snapshot in snapshots if snapshot["snapshot_id"] == snapshot_id), None)


def _flatten_snapshot_matches(bracket_data: dict[str, Any]) -> list[dict[str, Any]]:
    bracket = bracket_data.get("bracket", {})
    matches: list[dict[str, Any]] = []
    for stage_name in ("round_of_32", "round_of_16", "quarter_finals", "semi_finals"):
        matches.extend(bracket.get(stage_name, []))
    if bracket.get("third_place"):
        matches.append(bracket["third_place"])
    if bracket.get("final"):
        matches.append(bracket["final"])
    return matches


def _snapshot_match_lookup(snapshot_id: str) -> dict[str, dict[str, Any]]:
    predictions = probability_table(snapshot_id)
    bracket_data = load_latest_bracket(snapshot_id)
    lookup: dict[str, dict[str, Any]] = {}
    for prediction in predictions:
        lookup[prediction["match_id"]] = {"match_type": "group", "payload": prediction}
    for match in _flatten_snapshot_matches(bracket_data):
        lookup[match["match_id"]] = {"match_type": "knockout", "payload": match}
    return lookup


def _team_features_lookup(snapshot_id: str) -> dict[str, dict[str, Any]]:
    team_features = load_snapshot_file("team_features.json", snapshot_id=snapshot_id, default=[])
    return {row["team"]: row for row in team_features if isinstance(row, dict) and "team" in row}


def _snapshot_rosters(snapshot_id: str) -> dict[str, list[dict[str, Any]]]:
    roster_payload = load_snapshot_file("rosters.json", snapshot_id=snapshot_id, default={}) or {}
    return roster_payload if isinstance(roster_payload, dict) else {}


def _inject_styles(st: Any, dark_mode: bool = False) -> None:
    """Apply a clean tournament-board style to the dashboard with Light/Dark mode support."""

    theme_class = "dark-theme" if dark_mode else "light-theme"

    st.markdown(
        f"""
        { '<div class="dark-theme-trigger" style="display:none;"></div>' if dark_mode else '' }
        <style>
        :root {{
            --bg-color: #ffffff;
            --text-color: #10231f;
            --title-color: #0f3d35;
            --subtitle-color: #4b635d;
            --card-border: #d5e4df;
            --card-shadow: rgba(15, 61, 53, 0.08);
            --card-bg: #ffffff;
            --header-bg: #123f37;
            --header-text: #ffffff;
            --table-th-color: #5a726b;
            --table-th-border: #e6efec;
            --table-th-bg: #f7fbf9;
            --table-td-border: #edf3f1;
            --qual-row-bg: #eff9f4;
            --qual-pill-bg: #1f8f6a;
            --knockout-title: #123f37;
            --match-card-border: #dce8e4;
            --match-card-bg: #fcfefd;
            --match-round-text: #6f857f;
            --match-meta-text: #5f756f;
            --winner-mark: #1f8f6a;
            --champion-bg-start: #fffdf5;
            --champion-bg-end: #ffffff;
            --champion-label: #7b6a2d;
            --champion-odds: #556b65;
            --bracket-title-bg: #f0f7f4;
            --bracket-match-hover: rgba(15,61,53,0.12);
            --line-color: #cbdad5;
        }}
        
        /* The global dark mode overrides */
        .stApp.dark-theme,
        [data-testid="stAppViewContainer"]:has(.dark-theme-trigger) {{
            --bg-color: #0e1117;
            --text-color: #fafafa;
            --title-color: #e0f2ee;
            --subtitle-color: #a0b2ad;
            --card-border: #2a3633;
            --card-shadow: rgba(0, 0, 0, 0.4);
            --card-bg: #161b22;
            --header-bg: #1f2926;
            --header-text: #e0f2ee;
            --table-th-color: #8da49d;
            --table-th-border: #2a3633;
            --table-th-bg: #1c2220;
            --table-td-border: #242f2c;
            --qual-row-bg: #19362c;
            --qual-pill-bg: #10b981;
            --knockout-title: #e0f2ee;
            --match-card-border: #303e3a;
            --match-card-bg: #1b221f;
            --match-round-text: #8da49d;
            --match-meta-text: #8da49d;
            --winner-mark: #10b981;
            --champion-bg-start: #2d2610;
            --champion-bg-end: #161b22;
            --champion-label: #d4af37;
            --champion-odds: #a0b2ad;
            --bracket-title-bg: #1c2220;
            --bracket-match-hover: rgba(0,0,0,0.5);
            --line-color: #3b4e48;
        }}

        /* We rely on the hidden div above to trigger the :has selector if dark mode is active */

        .stApp {{
            background: var(--bg-color);
            color: var(--text-color);
        }}
        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }}
        .overview-shell {{
            background: transparent;
        }}
        .overview-title {{
            font-size: 2.35rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
            color: var(--title-color);
        }}
        .overview-subtitle {{
            color: var(--subtitle-color);
            font-size: 1rem;
            margin-bottom: 1.4rem;
        }}
        .group-card {{
            border: 1px solid var(--card-border);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 14px 28px var(--card-shadow);
            background: var(--card-bg);
            margin-bottom: 1rem;
        }}
        .group-card-body {{
            overflow-x: auto;
        }}
        .group-card-header {{
            background: var(--header-bg);
            color: var(--header-text);
            padding: 0.7rem 1rem;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        .group-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .group-table th {{
            text-align: left;
            padding: 0.6rem 0.75rem;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--table-th-color);
            border-bottom: 1px solid var(--table-th-border);
            background: var(--table-th-bg);
        }}
        .group-table td {{
            padding: 0.62rem 0.75rem;
            font-size: 0.92rem;
            border-bottom: 1px solid var(--table-td-border);
        }}
        .group-table tr:last-child td {{
            border-bottom: none;
        }}
        .qualified-row {{
            background: var(--qual-row-bg);
            font-weight: 700;
        }}
        .team-cell {{
            white-space: nowrap;
        }}
        .qual-pill {{
            display: inline-block;
            margin-left: 0.45rem;
            padding: 0.16rem 0.42rem;
            border-radius: 999px;
            background: var(--qual-pill-bg);
            color: #ffffff;
            font-size: 0.67rem;
            font-weight: 700;
            vertical-align: middle;
        }}
        .knockout-shell {{
            margin-top: 1.25rem;
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 1.2rem 1.2rem 0.8rem;
            box-shadow: 0 14px 28px var(--card-shadow);
            background: var(--card-bg);
        }}
        .knockout-title {{
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--knockout-title);
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .match-card {{
            border: 1px solid var(--match-card-border);
            border-radius: 16px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.85rem;
            background: var(--match-card-bg);
        }}
        .match-round {{
            color: var(--match-round-text);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.7rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
        }}
        .match-line {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            padding: 0.22rem 0;
            font-size: 0.96rem;
        }}
        .match-team {{
            font-weight: 700;
            color: var(--text-color);
        }}
        .match-meta {{
            font-size: 0.78rem;
            color: var(--match-meta-text);
        }}
        .winner-mark {{
            color: var(--winner-mark);
            font-weight: 800;
            margin-left: 0.35rem;
        }}
        .champion-card {{
            border: 1px solid var(--match-card-border);
            border-radius: 22px;
            background: linear-gradient(180deg, var(--champion-bg-start) 0%, var(--champion-bg-end) 100%);
            padding: 1.35rem 1rem;
            text-align: center;
            min-height: 100%;
        }}
        .champion-trophy {{
            font-size: 3rem;
            line-height: 1;
            margin-bottom: 0.65rem;
        }}
        .champion-label {{
            color: var(--champion-label);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.72rem;
            font-weight: 800;
        }}
        .champion-team {{
            margin-top: 0.4rem;
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--text-color);
        }}
        .champion-odds {{
            margin-top: 0.3rem;
            color: var(--champion-odds);
            font-size: 0.9rem;
        }}
        .snapshots-note {{
            color: var(--subtitle-color);
            font-size: 0.9rem;
            margin-top: 0.8rem;
        }}
        .flag-icon {{
            height: 1.1em;
            width: 1.5em;
            border-radius: 2px;
            vertical-align: text-bottom;
            margin-right: 0.3em;
            object-fit: cover;
            border: 1px solid var(--card-border);
        }}
        /* ── Full Knockout Bracket ── */
        .bracket-scroll {{
            overflow-x: auto;
            padding-bottom: 1rem;
        }}
        .bracket-container {{
            display: flex;
            align-items: stretch;
            gap: 0;
            min-width: max-content;
        }}
        .bracket-round {{
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            min-width: 200px;
            padding: 0 6px;
        }}
        .bracket-round-title {{
            text-align: center;
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--knockout-title);
            padding: 0.4rem 0;
            margin-bottom: 0.3rem;
            background: var(--bracket-title-bg);
            border-radius: 8px;
            position: sticky;
            top: 0;
            z-index: 2;
        }}
        
        .bracket-pair {{
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            position: relative;
            padding-right: 16px;
            margin: 4px 0;
            flex-grow: 1;
        }}
        .bracket-round:not(:last-child) .bracket-pair::after {{
            content: '';
            position: absolute;
            right: 0;
            top: 25%;
            bottom: 25%;
            width: 16px;
            border-right: 2px solid var(--line-color);
            border-top: 2px solid var(--line-color);
            border-bottom: 2px solid var(--line-color);
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}
        .bracket-round:not(:first-child) .bracket-match::before {{
            content: '';
            position: absolute;
            left: -22px;
            top: 50%;
            width: 16px;
            height: 2px;
            background: var(--line-color);
        }}

        .bracket-match {{
            border: 1px solid var(--match-card-border);
            border-radius: 10px;
            margin: 4px 0;
            background: var(--match-card-bg);
            overflow: hidden;
            font-size: 0.8rem;
            position: relative;
            transition: box-shadow 0.15s ease;
        }}
        .bracket-match:hover {{
            box-shadow: 0 4px 12px var(--bracket-match-hover);
        }}
        .bracket-team-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 5px 8px;
            gap: 4px;
            border-bottom: 1px solid var(--table-td-border);
        }}
        .bracket-team-row:last-child {{
            border-bottom: none;
        }}
        .bracket-team-row.is-winner {{
            background: var(--qual-row-bg);
            font-weight: 700;
        }}
        .bracket-team-name {{
            display: flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
            color: var(--text-color);
        }}
        .bracket-team-name .flag-icon {{
            height: 0.95em;
            width: 1.3em;
            flex-shrink: 0;
        }}
        .bracket-score {{
            font-weight: 700;
            color: var(--text-color);
            min-width: 16px;
            text-align: center;
        }}
        .bracket-path {{
            display: inline-block;
            margin-left: 4px;
            padding: 1px 5px;
            border-radius: 4px;
            font-size: 0.6rem;
            font-weight: 700;
            background: var(--bracket-title-bg);
            color: var(--match-round-text);
            white-space: nowrap;
            vertical-align: middle;
            letter-spacing: 0.03em;
        }}
        .bracket-annex-c {{
            text-align: center;
            font-size: 0.55rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--match-round-text);
            padding: 2px 0;
            border-bottom: 1px solid var(--table-td-border);
        }}
        .bracket-champion-banner {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-width: 180px;
            padding: 0 10px;
            position: relative;
        }}
        /* Line from Semi to Final */
        .bracket-champion-banner::before {{
            content: '';
            position: absolute;
            left: -16px;
            top: 50%;
            width: 16px;
            height: 2px;
            background: var(--line-color);
        }}
        .bracket-champion-inner {{
            border: 2px solid var(--champion-label);
            border-radius: 16px;
            background: linear-gradient(180deg, var(--champion-bg-start) 0%, var(--card-bg) 100%);
            padding: 1rem 1.2rem;
            text-align: center;
            width: 100%;
        }}
        .bracket-champion-inner .champion-trophy {{
            font-size: 2.2rem;
        }}
        .bracket-champion-inner .champion-label {{
            font-size: 0.65rem;
        }}
        .bracket-champion-inner .champion-team {{
            font-size: 1rem;
        }}
        .bracket-champion-inner .champion-odds {{
            font-size: 0.78rem;
        }}
        .bracket-third-place {{
            margin-top: 0.6rem;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 6px;
            width: 100%;
            background: var(--match-card-bg);
        }}
        .bracket-third-label {{
            text-align: center;
            font-size: 0.6rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--champion-label);
            margin-bottom: 3px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )



def _local_flag_b64(team: str) -> str:
    """Return base64 Data URI of local flag."""
    path = FLAGS_DIR / f"{team}.png"
    if path.exists():
        with open(path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    return ""

def _local_flag_html(team: str) -> str:
    """Return HTML img tag for local flag."""
    b64 = _local_flag_b64(team)
    if b64:
        return f'<img src="{b64}" class="flag-icon" />'
    return "🏳️"



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
                <td class="team-cell">{_local_flag_html(row['team'])} {row['team']}{qualifier}</td>
                <td>{row['points']}</td>
                <td>{row.get('wins', 0)}</td>
                <td>{row.get('draws', 0)}</td>
                <td>{row.get('losses', 0)}</td>
                <td>{row['goal_difference']}</td>
                <td>{row['goals_for']}</td>
            </tr>
            """
        )
    _render_html(
        st,
        f"""
        <div class="group-card">
            <div class="group-card-header">Group {group_id}</div>
            <div class="group-card-body">
                <table class="group-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Team</th>
                            <th>Pts</th>
                            <th>W</th>
                            <th>D</th>
                            <th>L</th>
                            <th>GD</th>
                            <th>GF</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table_rows)}
                    </tbody>
                </table>
            </div>
        </div>
        """)


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
            f'<span class="match-team">{_local_flag_html(team)} {team}{winner_mark}</span>'
            f'<span>{goals}</span>'
            f'</div>'
        )

    _render_html(
        st,
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
        """)


def _render_bracket_match_html(match: dict[str, Any]) -> str:
    """Return HTML for a single bracket match cell."""
    home = match.get("home_team", "TBD")
    away = match.get("away_team", "TBD")
    winner = match.get("winner", "")
    score = match.get("score", {})
    home_goals = score.get("home", "-")
    away_goals = score.get("away", "-")
    home_cls = ' is-winner' if home == winner else ''
    away_cls = ' is-winner' if away == winner else ''
    home_flag = _local_flag_html(home) if home != "TBD" else ""
    away_flag = _local_flag_html(away) if away != "TBD" else ""

    # Path labels (e.g., "1A", "2B", "3D", "WM74")
    home_path = match.get("home_path", "")
    away_path = match.get("away_path", "")
    home_path_html = f'<span class="bracket-path">{home_path}</span>' if home_path else ""
    away_path_html = f'<span class="bracket-path">{away_path}</span>' if away_path else ""

    # Annex C match number header (e.g., "M74")
    annex_c = match.get("annex_c", "")
    annex_header = f'<div class="bracket-annex-c">{annex_c}</div>' if annex_c else ""

    # Generate a unique ID for this match
    match_id = match.get("match_id", f"{home}_{away}").replace(" ", "_")

    # The javascript safely finds the hidden stream button by its text content and clicks it
    onclick_js = (
        f"var btns = Array.from(window.parent.document.querySelectorAll('button')); "
        f"var btn = btns.find(b => b.innerText.includes('hidden_{match_id}')); "
        f"if (btn) btn.click();"
    )

    return (
        f'<div class="bracket-match" style="cursor: pointer;" onclick="{onclick_js}" title="Click to analyze match">'
        f'{annex_header}'
        f'<div class="bracket-team-row{home_cls}">'
        f'<span class="bracket-team-name">{home_flag}{home}{home_path_html}</span>'
        f'<span class="bracket-score">{home_goals}</span>'
        f'</div>'
        f'<div class="bracket-team-row{away_cls}">'
        f'<span class="bracket-team-name">{away_flag}{away}{away_path_html}</span>'
        f'<span class="bracket-score">{away_goals}</span>'
        f'</div>'
        f'</div>'
    )


def _render_knockout_bracket(st: Any, bracket: dict[str, Any], champion_odds: dict[str, float], snapshot_id: str) -> None:
    """Render the full knockout bracket from R32 to Final as a horizontally scrollable tree."""

    rounds_config = [
        ("Round of 32", bracket.get("round_of_32", [])),
        ("Round of 16", bracket.get("round_of_16", [])),
        ("Quarter-finals", bracket.get("quarter_finals", [])),
        ("Semi-finals", bracket.get("semi_finals", [])),
    ]
    final_match = bracket.get("final")
    third_place = bracket.get("third_place")
    champion = final_match.get("winner") if final_match else None

    # Build round columns HTML
    rounds_html = []
    for title, matches in rounds_config:
        if not matches:
            continue
            
        match_pairs_html = []
        for i in range(0, len(matches), 2):
            pair = matches[i:i+2]
            pair_html = "".join(_render_bracket_match_html(m) for m in pair)
            match_pairs_html.append(f'<div class="bracket-pair">{pair_html}</div>')
            
        rounds_html.append(
            f'<div class="bracket-round">'
            f'<div class="bracket-round-title">{title}</div>'
            f'{"".join(match_pairs_html)}'
            f'</div>'
        )

    # Final + Champion column
    champion_flag = _local_flag_html(champion) if champion else ""
    champion_prob = champion_odds.get(champion, 0.0) if champion else 0.0
    final_html = _render_bracket_match_html(final_match) if final_match else ""
    third_html = ""
    if third_place:
        third_html = (
            f'<div class="bracket-third-place">'
            f'<div class="bracket-third-label">3rd Place</div>'
            f'{_render_bracket_match_html(third_place)}'
            f'</div>'
        )

    champion_col_html = (
        f'<div class="bracket-champion-banner">'
        f'<div class="bracket-round-title">Final</div>'
        f'{final_html}'
        f'<div class="bracket-champion-inner" style="margin-top:8px;">'
        f'<div class="champion-trophy">{champion_flag if champion else "🏆"}</div>'
        f'<div class="champion-label">Projected Champion</div>'
        f'<div class="champion-team">{champion_flag} {champion if champion else "TBD"}</div>'
        f'<div class="champion-odds">{champion_prob:.1%} title probability</div>'
        f'</div>'
        f'{third_html}'
        f'</div>'
    )
    rounds_html.append(champion_col_html)

    full_html = (
        '<div class="bracket-scroll">'
        '<div class="bracket-container">'
        + "".join(rounds_html)
        + '</div></div>'
    )
    st.markdown(full_html, unsafe_allow_html=True)
    
    # The bracket remains snapshot-backed, but we avoid hidden helper controls here
    # because broad CSS selectors can accidentally blank the whole page in Streamlit.


def _render_overview(st: Any, snapshot_id: str) -> None:
    """Render the tournament-board overview."""

    standings = load_latest_standings(snapshot_id)
    bracket_data = load_latest_bracket(snapshot_id)
    snapshots = list_snapshot_timeline()

    if not snapshots:
        st.warning("No baseline snapshot is available yet.")
        if st.button("Build Baseline Snapshot", key="build_baseline_snapshot"):
            with st.spinner("Building baseline tournament snapshot..."):
                _ensure_baseline_snapshot()
            st.rerun()
        return

    champion_odds = bracket_data.get("champion_odds", {})
    bracket = bracket_data.get("bracket", {})

    _render_html(
        st,
        """
<div class="overview-shell">
<div class="overview-title">Tournament Overview</div>
<div class="overview-subtitle">Group leaders and qualifiers at the top, knockout bracket underneath.</div>
</div>
        """)

    if standings:
        groups = sorted(standings.items())
        for row_start in range(0, len(groups), 3):
            columns = st.columns(3)
            for column, (group_id, rows) in zip(columns, groups[row_start : row_start + 3]):
                with column:
                    _render_group_card(st, group_id, rows)
    else:
        st.info("No standings snapshot is available yet.")

    _render_html(st, '<div class="knockout-shell"><div class="knockout-title">Knockout Bracket</div></div>')

    if bracket:
        _render_knockout_bracket(st, bracket, champion_odds, snapshot_id)
    else:
        st.info("No knockout bracket data available yet.")

    if snapshots:
        _render_html(
            st,
            f'<div class="snapshots-note">Snapshots loaded: {", ".join(snapshot["snapshot_id"] for snapshot in snapshots)}</div>',
        )



def show_match_analysis_modal(home: str, away: str, match_id: str | None = None):
    import streamlit as st
    from src.models.train import load_or_train_ensemble
    from src.simulation.penalties import penalty_home_probability

    @st.cache_resource
    def get_cached_model(model_version: float):
        return load_or_train_ensemble()

    model_version = ENSEMBLE_MODEL_FILE.stat().st_mtime if ENSEMBLE_MODEL_FILE.exists() else 0.0
    model = get_cached_model(model_version)
    
    @st.dialog(f"Match Analysis", width="large")
    def _modal():
        st.markdown(f"### {_local_flag_html(home)} {home} vs {_local_flag_html(away)} {away}", unsafe_allow_html=True)
        st.write(f"**Prediction Details**")

        try:
            prediction = model.predict_match(home, away, match_id=match_id)
        except ValueError as exc:
            if "Feature names should match" not in str(exc):
                raise
            get_cached_model.clear()
            refreshed_model = load_or_train_ensemble(force=True)
            prediction = refreshed_model.predict_match(home, away, match_id=match_id)

        probs = prediction["outcome_probabilities"]
        score = prediction["predicted_score"]
        penalty_home = penalty_home_probability(
            prediction["features"]["home_penalty_win_rate"],
            prediction["features"]["away_penalty_win_rate"],
            prediction["features"]["elo_diff"],
        )
        home_advance = probs["home_win"] + probs["draw"] * penalty_home
        away_advance = probs["away_win"] + probs["draw"] * (1.0 - penalty_home)
        
        st.write(f"**Predicted Score**: {home} {score['home']} - {score['away']} {away}")
        st.write(f"**Win Probabilities**: {home} ({probs['home_win']:.1%}) | Draw ({probs['draw']:.1%}) | {away} ({probs['away_win']:.1%})")
        st.write(f"**If Knockout: Advance Odds**: {home} ({home_advance:.1%}) | {away} ({away_advance:.1%})")
        st.write(f"**Confidence**: {prediction['confidence']['label']} ({prediction['confidence']['overall']}/100)")
        
        st.markdown("""
        <style>
        div[data-testid="stExpander"]:has(summary:contains("How is this prediction made?")) {
            border: 2px solid #ffbf00;
            background-color: rgba(255, 191, 0, 0.05);
            border-radius: 8px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.expander("How is this prediction made?", expanded=False):
            st.markdown("**Key Factors Driving This Prediction**")
            
            home_stats = model.team_lookup.get(home, {})
            away_stats = model.team_lookup.get(away, {})
            reasons = []
            
            elo_diff = home_stats.get('elo', 0) - away_stats.get('elo', 0)
            if abs(elo_diff) > 100:
                favored = home if elo_diff > 0 else away
                reasons.append(f"**Elo Rating Advantage**: {favored} holds a significantly higher historical Elo rating (+{int(abs(elo_diff))} points).")
                
            val_diff = home_stats.get('squad_market_value', 0) - away_stats.get('squad_market_value', 0)
            val_diff_m = val_diff / 1e6
            if abs(val_diff_m) > 50:
                favored = home if val_diff_m > 0 else away
                reasons.append(f"**Squad Quality**: {favored}'s squad has a significantly higher market value (+€{int(abs(val_diff_m))}M), reflecting superior talent and depth.")
                
            form_diff = home_stats.get('form_points_avg', 0) - away_stats.get('form_points_avg', 0)
            if abs(form_diff) > 0.5:
                favored = home if form_diff > 0 else away
                reasons.append(f"**Recent Momentum**: {favored} is entering the match in much better recent form.")
                
            h2h = get_head_to_head(home, away)
            summary = h2h.get("summary", {})
            if summary and summary.get("total_matches", 0) >= 3:
                h_wins = summary.get(home + '_wins', 0)
                a_wins = summary.get(away + '_wins', 0)
                if h_wins > a_wins and (h_wins - a_wins) >= 2:
                    reasons.append(f"**Historical Dominance**: {home} has historically dominated this fixture, winning {h_wins} out of {summary.get('total_matches')} meetings.")
                elif a_wins > h_wins and (a_wins - h_wins) >= 2:
                    reasons.append(f"**Historical Dominance**: {away} has historically dominated this fixture, winning {a_wins} out of {summary.get('total_matches')} meetings.")
                    
            if not reasons:
                reasons.append("This is an extremely tightly contested match with no major disparities in Elo, squad value, or form. The prediction leans on minor tactical, depth, or home-field advantages.")
                
            for r in reasons:
                st.markdown(f"- {r}")
                
            st.markdown("*(Powered by an Adaptive Ensemble Model combining XGBoost, Random Forest, Poisson Regression, and Elo Ratings)*")
        
        st.divider()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Head-to-Head History")
            if summary:
                st.write(f"**Total Matches**: {summary.get('total_matches', 0)}")
                st.write(f"**{home} Wins**: {summary.get(home + '_wins', 0)} | **{away} Wins**: {summary.get(away + '_wins', 0)} | **Draws**: {summary.get('draws', 0)}")
                
                if h2h.get("recent_matches"):
                    st.write("**Recent Matches:**")
                    for m in h2h["recent_matches"]:
                        st.caption(f"{m['date']} - {m['tournament']}: {m['home_team']} {m['home_goals']} - {m['away_goals']} {m['away_team']}")
            else:
                st.info("No historical matches found between these teams.")
                
        with col2:
            st.subheader("Team Comparison")
            
            import plotly.graph_objects as go
            
            metrics = [
                ("Elo Rating", "elo"),
                ("Squad Rating", "squad_avg_rating"),
                ("Starting XI Rating", "starting_xi_rating"),
                ("Form", "form_points_avg"),
                ("Attack", "attack_strength"),
                ("Defense", "defense_strength")
            ]
            
            y_labels = []
            home_vals = []
            away_vals = []
            
            for label, key in metrics:
                h_val = home_stats.get(key, 0)
                a_val = away_stats.get(key, 0)
                
                y_labels.append(label)
                home_vals.append(h_val)
                away_vals.append(a_val)
                
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=y_labels,
                x=[-x for x in home_vals], # Negative to plot left
                name=home,
                orientation='h',
                marker=dict(color='#1f8f6a'),
                text=[f"{x:.1f}" for x in home_vals],
                textposition='outside'
            ))
            fig.add_trace(go.Bar(
                y=y_labels,
                x=away_vals,
                name=away,
                orientation='h',
                marker=dict(color='#123f37'),
                text=[f"{x:.1f}" for x in away_vals],
                textposition='outside'
            ))
            
            fig.update_layout(
                barmode='relative',
                title_text="Team Strengths Comparison",
                yaxis=dict(autorange="reversed"),
                xaxis=dict(showticklabels=False),
                margin=dict(l=0, r=0, t=30, b=0),
                height=300,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        with st.expander("Squad Comparison", expanded=False):
            from src.config import ROSTERS_FILE
            if ROSTERS_FILE.exists():
                roster_payload = load_json(ROSTERS_FILE, default={}) or {}
                roster_rows: list[dict[str, Any]] = []

                if isinstance(roster_payload, dict):
                    for team_name, players in roster_payload.items():
                        if not isinstance(players, list):
                            continue
                        for player in players:
                            if not isinstance(player, dict):
                                continue
                            roster_rows.append(
                                {
                                    "team": team_name,
                                    "short_name": player.get("short_name", player.get("name", "Unknown")),
                                    "club_name": player.get("club_name", player.get("club", "Unknown")),
                                    "overall": player.get("overall", player.get("rating", 0)),
                                    "market_value_eur": player.get("market_value_eur", player.get("value", 0)),
                                }
                            )
                elif isinstance(roster_payload, list):
                    roster_rows = [row for row in roster_payload if isinstance(row, dict)]

                rosters = pd.DataFrame(roster_rows)
                if not rosters.empty:
                    for column in ("team", "short_name", "club_name"):
                        if column not in rosters:
                            rosters[column] = ""
                    for column in ("overall", "market_value_eur"):
                        if column not in rosters:
                            rosters[column] = 0
                        rosters[column] = pd.to_numeric(rosters[column], errors="coerce").fillna(0)
                
                def render_squad(team_name):
                    team_roster = rosters[rosters['team'] == team_name]
                    if not team_roster.empty:
                        # Compute overall value
                        total_value = team_roster['market_value_eur'].sum()
                        avg_rating = team_roster['overall'].mean()
                        val_m = total_value / 1_000_000
                        st.markdown(f"**Total Squad Value**: €{val_m:,.1f}M  |  **Avg Rating**: {avg_rating:.1f}")
                        
                        display_cols = ['short_name', 'club_name', 'overall', 'market_value_eur']
                        df_show = team_roster[display_cols].sort_values('overall', ascending=False)
                        st.dataframe(
                            df_show, 
                            hide_index=True,
                            column_config={
                                "short_name": "Player",
                                "club_name": "Club",
                                "overall": st.column_config.NumberColumn("Rating", format="%d"),
                                "market_value_eur": st.column_config.NumberColumn("Value (€)", format="%d")
                            },
                            height=300
                        )
                    else:
                        st.info("No squad data available.")
                        
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.markdown(f"#### {home}")
                    render_squad(home)
                with sc2:
                    st.markdown(f"#### {away}")
                    render_squad(away)

    # actually invoke the dialog
    _modal()


def show_snapshot_match_analysis_modal(home: str, away: str, snapshot_id: str, match_id: str | None = None):
    import plotly.graph_objects as go
    import streamlit as st

    match_lookup = _snapshot_match_lookup(snapshot_id)
    match_record = match_lookup.get(match_id or "")
    team_lookup = _team_features_lookup(snapshot_id)
    rosters = _snapshot_rosters(snapshot_id)
    snapshot_state = load_snapshot_file("state.json", snapshot_id=snapshot_id, default={})

    @st.dialog("Match Analysis", width="large")
    def _modal():
        st.markdown(f"### {_local_flag_html(home)} {home} vs {_local_flag_html(away)} {away}", unsafe_allow_html=True)
        if not match_record:
            st.info("This match is not available in the selected snapshot.")
            return

        payload = match_record["payload"]
        if match_record["match_type"] == "group":
            prediction = payload.get("prediction_details", {})
            score_home = payload.get("predicted_home_goals", "-")
            score_away = payload.get("predicted_away_goals", "-")
            probs = {
                "home_win": payload.get("home_win_probability", 0.0),
                "draw": payload.get("draw_probability", 0.0),
                "away_win": payload.get("away_win_probability", 0.0),
            }
            advancement = {}
            confidence_label = payload.get("confidence_label", "Unknown")
            confidence_value = payload.get("confidence", 0.0)
        else:
            prediction = payload.get("prediction", {})
            score_home = payload.get("score", {}).get("home", "-")
            score_away = payload.get("score", {}).get("away", "-")
            probs = prediction.get("outcome_probabilities", {})
            advancement = prediction.get("advancement_probabilities", {})
            confidence_label = prediction.get("confidence", {}).get("label", "Unknown")
            confidence_value = prediction.get("confidence", {}).get("overall", 0.0)

        st.write(f"**Predicted Score**: {home} {score_home} - {score_away} {away}")
        st.write(f"**Win Probabilities**: {home} ({probs.get('home_win', 0.0):.1%}) | Draw ({probs.get('draw', 0.0):.1%}) | {away} ({probs.get('away_win', 0.0):.1%})")
        if advancement:
            st.write(f"**Advance Odds**: {home} ({advancement.get('home', 0.0):.1%}) | {away} ({advancement.get('away', 0.0):.1%})")
        st.write(f"**Confidence**: {confidence_label} ({confidence_value}/100)")

        state_row = snapshot_state.get(match_id or "", {})
        if state_row.get("state") == "RESOLVED":
            st.success(
                f"Resolved in this snapshot: {state_row.get('home_team', home)} {state_row.get('home_goals')} - {state_row.get('away_goals')} {state_row.get('away_team', away)}"
            )

        with st.expander("Snapshot Inputs", expanded=False):
            features = prediction.get("features", {})
            contextual = prediction.get("contextual_factors", {})
            if features:
                st.markdown("**Features**")
                st.json(features)
            if contextual:
                st.markdown("**Contextual Factors**")
                st.json(contextual)
            if not features and not contextual:
                st.info("This snapshot stores only summary prediction data for this match.")

        home_stats = team_lookup.get(home, {})
        away_stats = team_lookup.get(away, {})
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Snapshot Team Features")
            if home_stats or away_stats:
                metrics = [
                    ("Elo", "elo"),
                    ("Ranking", "ranking_points"),
                    ("Form", "form_points_avg"),
                    ("Attack", "attack_strength"),
                    ("Defense", "defense_strength"),
                    ("Squad Rating", "squad_avg_rating"),
                ]
                for label, key in metrics:
                    st.write(f"**{label}**: {home} {float(home_stats.get(key, 0) or 0):.2f} | {away} {float(away_stats.get(key, 0) or 0):.2f}")
            else:
                st.info("No team features saved in this snapshot.")

        with col2:
            st.subheader("Team Comparison")
            metrics = [
                ("Elo Rating", "elo"),
                ("Squad Rating", "squad_avg_rating"),
                ("Starting XI Rating", "starting_xi_rating"),
                ("Form", "form_points_avg"),
                ("Attack", "attack_strength"),
                ("Defense", "defense_strength"),
            ]
            y_labels = [label for label, _ in metrics]
            home_vals = [float(home_stats.get(key, 0) or 0) for _, key in metrics]
            away_vals = [float(away_stats.get(key, 0) or 0) for _, key in metrics]
            fig = go.Figure()
            fig.add_trace(go.Bar(y=y_labels, x=[-value for value in home_vals], name=home, orientation="h", marker=dict(color="#1f8f6a"), text=[f"{value:.1f}" for value in home_vals], textposition="outside"))
            fig.add_trace(go.Bar(y=y_labels, x=away_vals, name=away, orientation="h", marker=dict(color="#123f37"), text=[f"{value:.1f}" for value in away_vals], textposition="outside"))
            fig.update_layout(barmode="relative", title_text="Snapshot Team Strengths", yaxis=dict(autorange="reversed"), xaxis=dict(showticklabels=False), margin=dict(l=0, r=0, t=30, b=0), height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with st.expander("Squad Comparison", expanded=False):
            roster_rows: list[dict[str, Any]] = []
            for team_name, players in rosters.items():
                if not isinstance(players, list):
                    continue
                for player in players:
                    if not isinstance(player, dict):
                        continue
                    roster_rows.append({"team": team_name, "short_name": player.get("short_name", player.get("name", "Unknown")), "club_name": player.get("club_name", player.get("club", "Unknown")), "overall": player.get("overall", player.get("rating", 0)), "market_value_eur": player.get("market_value_eur", player.get("value", 0))})
            rosters_frame = pd.DataFrame(roster_rows)
            if rosters_frame.empty:
                st.info("No roster data saved in this snapshot.")
            else:
                rosters_frame["overall"] = pd.to_numeric(rosters_frame["overall"], errors="coerce").fillna(0)
                rosters_frame["market_value_eur"] = pd.to_numeric(rosters_frame["market_value_eur"], errors="coerce").fillna(0)

                def render_squad(team_name: str) -> None:
                    team_roster = rosters_frame[rosters_frame["team"] == team_name]
                    if team_roster.empty:
                        st.info("No squad data available.")
                        return
                    total_value = team_roster["market_value_eur"].sum() / 1_000_000
                    avg_rating = team_roster["overall"].mean()
                    st.markdown(f"**Total Squad Value**: EUR {total_value:,.1f}M  |  **Avg Rating**: {avg_rating:.1f}")
                    st.dataframe(team_roster[["short_name", "club_name", "overall", "market_value_eur"]].sort_values("overall", ascending=False), hide_index=True, column_config={"short_name": "Player", "club_name": "Club", "overall": st.column_config.NumberColumn("Rating", format="%d"), "market_value_eur": st.column_config.NumberColumn("Value (EUR)", format="%d")}, height=300)

                squad_col1, squad_col2 = st.columns(2)
                with squad_col1:
                    st.markdown(f"#### {home}")
                    render_squad(home)
                with squad_col2:
                    st.markdown(f"#### {away}")
                    render_squad(away)

    _modal()



def main() -> None:
    """Launch the optional Streamlit dashboard if available."""

    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise SystemExit("Streamlit is not installed. Install requirements to use the dashboard.") from exc

    st.set_page_config(page_title="World Cup Prediction Baseline", layout="wide")
    snapshots = list_snapshot_timeline()
    if not snapshots:
        _ensure_baseline_snapshot()
        snapshots = list_snapshot_timeline()
    
    # Place toggle in the sidebar or at the top of the page. Top of page is fine.
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.title("World Cup Prediction Baseline")
        st.caption("Offline demo pipeline with adaptive snapshots.")
    with col2:
        dark_mode = st.toggle("🌙 Dark Mode", value=False)
        
    selected_snapshot_id = snapshots[-1]["snapshot_id"] if snapshots else ""
    selected_snapshot = _find_snapshot(selected_snapshot_id, snapshots) if snapshots else None
    if snapshots:
        selected_snapshot_id = st.selectbox(
            "Snapshot",
            options=[snapshot["snapshot_id"] for snapshot in snapshots],
            index=len(snapshots) - 1,
            format_func=lambda snapshot_id: _snapshot_label(
                _find_snapshot(snapshot_id, snapshots)
                or {"snapshot_id": snapshot_id, "descriptor": snapshot_id, "resolved_matches": [], "model_metadata": {}}
            ),
        )
        selected_snapshot = _find_snapshot(selected_snapshot_id, snapshots)

    _inject_styles(st, dark_mode=dark_mode)
    if selected_snapshot is not None:
        current_model = current_model_metadata()
        selected_signature = ((selected_snapshot.get("model_metadata") or {}).get("signature")) or "unknown"
        if selected_signature != current_model["signature"]:
            st.warning(
                f"Selected snapshot uses model `{selected_signature}` while current artifacts are `{current_model['signature']}`."
            )
            if st.button("Refresh Selected Snapshot For Current Model", key="refresh_selected_snapshot"):
                with st.spinner("Refreshing selected snapshot with the current trained model..."):
                    _refresh_snapshot(selected_snapshot_id)
                st.rerun()

    overview, standings_tab, predictions_tab, accuracy_tab, compare_tab = st.tabs(
        ["Overview", "Standings", "Predictions", "Accuracy", "Compare"]
    )

    with overview:
        _render_overview(st, selected_snapshot_id)

    with standings_tab:
        st.subheader("Current Group Standings")
        standings = load_latest_standings(selected_snapshot_id)
        if standings:
            for group_id, rows in sorted(standings.items()):
                st.markdown(f"### Group {group_id}")
                frame = pd.DataFrame(_sorted_group_rows(rows))
                frame["Flag"] = frame["team"].apply(_local_flag_b64)
                frame["Team"] = frame.apply(
                    lambda row: row['team'] + ("  (QUALIFIED)" if row["qualified"] else ""),
                    axis=1,
                )
                st.dataframe(
                    frame[["Flag", "Team", "points", "wins", "draws", "losses", "goal_difference", "goals_for", "goals_against", "played"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Flag": st.column_config.ImageColumn(width="small")}
                )
        else:
            st.info("No standings snapshot is available yet.")

    with predictions_tab:
        st.subheader("Match Predictions")
        st.caption("Click a row to view detailed match analysis.")
        table = probability_table(selected_snapshot_id)
        if table:
            frame = pd.DataFrame(table)
            if "prediction_details" in frame.columns:
                frame = frame.drop(columns=["prediction_details"])
            
            from src.config import RAW_FIXTURES_FILE
            if RAW_FIXTURES_FILE.exists():
                fixtures = pd.read_csv(RAW_FIXTURES_FILE)
                if "date" in fixtures.columns and "match_id" in fixtures.columns:
                    frame = frame.merge(fixtures[["match_id", "date"]], on="match_id", how="left")
                    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%b %d, %H:%M")
            
            # Keep original names for the callback before mapping flags
            clean_frame = frame.copy()
            
            frame["home_flag"] = frame["home_team"].apply(_local_flag_b64)
            frame["away_flag"] = frame["away_team"].apply(_local_flag_b64)
            
            ordered_cols = []
            if "date" in frame.columns:
                ordered_cols.append("date")
            ordered_cols.extend(["home_flag", "home_team", "away_flag", "away_team"])
            
            for c in frame.columns:
                if c not in ordered_cols and c not in ["home_flag", "away_flag"]:
                    ordered_cols.append(c)
            
            event = st.dataframe(
                frame[ordered_cols], 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "date": "Date",
                    "home_flag": st.column_config.ImageColumn("Home Flag", width="small"),
                    "away_flag": st.column_config.ImageColumn("Away Flag", width="small"),
                    "home_team": "Home Team",
                    "away_team": "Away Team"
                }
            )
            
            if event.selection.rows:
                selected_idx = event.selection.rows[0]
                home = clean_frame.iloc[selected_idx]["home_team"]
                away = clean_frame.iloc[selected_idx]["away_team"]
                match_id = clean_frame.iloc[selected_idx]["match_id"]
                
                show_snapshot_match_analysis_modal(home, away, selected_snapshot_id, match_id)

    with accuracy_tab:
        st.subheader("Snapshot Accuracy Summary")
        st.json(accuracy_summary(selected_snapshot_id))

    with compare_tab:
        st.write("Selected snapshot metadata")
        if selected_snapshot is not None:
            st.json(selected_snapshot)


if __name__ == "__main__":
    main()

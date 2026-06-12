import re

with open("src/visualization/dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
if "import base64" not in content:
    content = content.replace("import pandas as pd", "import base64\nimport pandas as pd\nfrom src.config import FLAGS_DIR")

# 2. Flag dictionaries
content = re.sub(r"FLAG_BY_TEAM = \{[^}]+\}\n\n", "", content)

# 3. _flag function
flag_func = """def _local_flag_b64(team: str) -> str:
    \"\"\"Return base64 Data URI of local flag.\"\"\"
    path = FLAGS_DIR / f"{team}.png"
    if path.exists():
        with open(path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    return ""

def _local_flag_html(team: str) -> str:
    \"\"\"Return HTML img tag for local flag.\"\"\"
    b64 = _local_flag_b64(team)
    if b64:
        return f'<img src="{b64}" class="flag-icon" />'
    return "🏳️"
"""
content = re.sub(r"def _flag\(team: str\) -> str:.*?return FLAG_BY_TEAM\.get\(team, \".*?\"\)", flag_func, content, flags=re.DOTALL)

# 4. CSS style
css_addon = """        .flag-icon {
            height: 1.1em;
            width: 1.5em;
            border-radius: 2px;
            vertical-align: text-bottom;
            margin-right: 0.3em;
            object-fit: cover;
            border: 1px solid #dce8e4;
        }
        </style>"""
content = content.replace("        </style>", css_addon)

# 5. _render_group_card
content = content.replace("{_flag(row['team'])}", "{_local_flag_html(row['team'])}")

# 6. _render_match_card
content = content.replace("{_flag(team)}", "{_local_flag_html(team)}")

# 7. _render_overview
content = content.replace("_flag(champion)", "_local_flag_html(champion)")

# 8. Standings tab dataframe
standings_old = """                frame["team"] = frame.apply(
                    lambda row: f"{_flag(row['team'])} {row['team']}" + ("  QUALIFIED" if row["qualified"] else ""),
                    axis=1,
                )
                st.dataframe(
                    frame[["team", "points", "goal_difference", "goals_for", "goals_against", "played"]],
                    use_container_width=True,
                    hide_index=True,
                )"""
standings_new = """                frame["Flag"] = frame["team"].apply(_local_flag_b64)
                frame["Team"] = frame.apply(
                    lambda row: row['team'] + ("  (QUALIFIED)" if row["qualified"] else ""),
                    axis=1,
                )
                st.dataframe(
                    frame[["Flag", "Team", "points", "goal_difference", "goals_for", "goals_against", "played"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Flag": st.column_config.ImageColumn(width="small")}
                )"""
content = content.replace(standings_old, standings_new)

# 9. Predictions tab dataframe
preds_old = """            for column in ("home_team", "away_team"):
                frame[column] = frame[column].map(lambda team: f"{_flag(team)} {team}")
            
            event = st.dataframe(
                frame, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )"""
preds_new = """            frame["home_flag"] = frame["home_team"].apply(_local_flag_b64)
            frame["away_flag"] = frame["away_team"].apply(_local_flag_b64)
            
            ordered_cols = ["home_flag", "home_team", "away_flag", "away_team"]
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
                    "home_flag": st.column_config.ImageColumn("Home Flag", width="small"),
                    "away_flag": st.column_config.ImageColumn("Away Flag", width="small"),
                    "home_team": "Home Team",
                    "away_team": "Away Team"
                }
            )"""
content = content.replace(preds_old, preds_new)

# 10. Dialog
dialog_old = """@st.dialog(f"Match Analysis: {_flag(home)} {home} vs {_flag(away)} {away}", width="large")
                def match_analysis_modal():
                    st.write(f"### Prediction Details")"""
dialog_new = """@st.dialog(f"Match Analysis", width="large")
                def match_analysis_modal():
                    st.markdown(f"### {_local_flag_html(home)} {home} vs {_local_flag_html(away)} {away}", unsafe_allow_html=True)
                    st.write(f"**Prediction Details**")"""
content = content.replace(dialog_old, dialog_new)

with open("src/visualization/dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)

print("done")

import re

with open('src/visualization/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update _render_bracket_match_html
old_bracket_html = '''def _render_bracket_match_html(match: dict[str, Any]) -> str:
    \"\"\"Return HTML for a single bracket match cell.\"\"\"
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
    return (
        f'<div class="bracket-match">'
        f'<div class="bracket-team-row{home_cls}">'
        f'<span class="bracket-team-name">{home_flag}{home}</span>'
        f'<span class="bracket-score">{home_goals}</span>'
        f\\'</div>\\'
        f'<div class="bracket-team-row{away_cls}">'
        f'<span class="bracket-team-name">{away_flag}{away}</span>'
        f'<span class="bracket-score">{away_goals}</span>'
        f\\'</div>\\'
        f\\'</div>\\'
    )'''

new_bracket_html = '''def _render_bracket_match_html(match: dict[str, Any]) -> str:
    \"\"\"Return HTML for a single bracket match cell.\"\"\"
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
    
    # Generate a unique ID for this match
    match_id = match.get("match_id", f"{home}_{away}").replace(" ", "_")
    
    # The javascript safely finds the hidden stream button inside our span and clicks it
    onclick_js = (
        f"var btn = window.parent.document.querySelector('.hidden-btn-{match_id} button'); "
        f"if (btn) btn.click();"
    )
    
    return (
        f'<div class="bracket-match" style="cursor: pointer;" onclick="{onclick_js}" title="Click to analyze match">'
        f'<div class="bracket-team-row{home_cls}">'
        f'<span class="bracket-team-name">{home_flag}{home}</span>'
        f'<span class="bracket-score">{home_goals}</span>'
        f\\'</div>\\'
        f'<div class="bracket-team-row{away_cls}">'
        f'<span class="bracket-team-name">{away_flag}{away}</span>'
        f'<span class="bracket-score">{away_goals}</span>'
        f\\'</div>\\'
        f\\'</div>\\'
    )'''

content = content.replace(old_bracket_html, new_bracket_html)

# 2. Add hidden buttons at the end of _render_knockout_bracket
# Before the end of _render_knockout_bracket, it has:
#         '<div class="bracket-container">'
#         + "".join(rounds_html)
#         + '</div></div>'
#     )
#     st.markdown(full_html, unsafe_allow_html=True)

old_end_bracket = '''    full_html = (
        '<div class="bracket-scroll">'
        '<div class="bracket-container">'
        + "".join(rounds_html)
        + '</div></div>'
    )
    st.markdown(full_html, unsafe_allow_html=True)'''

new_end_bracket = '''    full_html = (
        '<div class="bracket-scroll">'
        '<div class="bracket-container">'
        + "".join(rounds_html)
        + '</div></div>'
    )
    st.markdown(full_html, unsafe_allow_html=True)
    
    # Render hidden Streamlit buttons to handle JS clicks from the HTML above
    st.markdown('<div style="opacity:0; height:0; width:0; overflow:hidden;">', unsafe_allow_html=True)
    all_matches = []
    for title, matches in rounds_config:
        if matches:
            all_matches.extend(matches)
    if final_match:
        all_matches.append(final_match)
    if third_place:
        all_matches.append(third_place)
        
    for m in all_matches:
        home = m.get("home_team", "TBD")
        away = m.get("away_team", "TBD")
        if home != "TBD" and away != "TBD":
            match_id = m.get("match_id", f"{home}_{away}").replace(" ", "_")
            st.markdown(f'<span class="hidden-btn-{match_id}">', unsafe_allow_html=True)
            if st.button(f"hidden_{match_id}", key=f"btn_hidden_{match_id}"):
                show_match_analysis_modal(home, away)
            st.markdown('</span>', unsafe_allow_html=True)
            
    st.markdown('</div>', unsafe_allow_html=True)'''

content = content.replace(old_end_bracket, new_end_bracket)

with open('src/visualization/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

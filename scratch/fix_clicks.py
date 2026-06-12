import re

with open('src/visualization/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the onclick JS
old_bracket_html = '''    # The javascript safely finds the hidden stream button inside our span and clicks it
    onclick_js = (
        f"var btn = window.parent.document.querySelector('.hidden-btn-{match_id} button'); "
        f"if (btn) btn.click();"
    )'''

new_bracket_html = '''    # The javascript safely finds the hidden stream button by its text content and clicks it
    onclick_js = (
        f"var btns = Array.from(window.parent.document.querySelectorAll('button')); "
        f"var btn = btns.find(b => b.innerText.includes('hidden_{match_id}')); "
        f"if (btn) btn.click();"
    )'''

content = content.replace(old_bracket_html, new_bracket_html)

# Fix the button rendering and hiding
old_button_render = '''    # Render hidden Streamlit buttons to handle JS clicks from the HTML above
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

new_button_render = '''    # Render hidden Streamlit buttons to handle JS clicks from the HTML above
    with st.container():
        st.markdown('<div class="hidden-button-marker" style="display:none;"></div>', unsafe_allow_html=True)
        st.markdown(
            \"\"\"
            <style>
            /* Hide the container that holds the marker */
            div[data-testid="stVerticalBlock"]:has(.hidden-button-marker) {
                display: none !important;
            }
            </style>
            \"\"\",
            unsafe_allow_html=True
        )
        
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
                if st.button(f"hidden_{match_id}", key=f"btn_hidden_{match_id}"):
                    show_match_analysis_modal(home, away)'''

content = content.replace(old_button_render, new_button_render)

with open('src/visualization/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

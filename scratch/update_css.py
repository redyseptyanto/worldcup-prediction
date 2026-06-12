import re

with open('src/visualization/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define new _inject_styles
new_inject_styles = '''def _inject_styles(st: Any, dark_mode: bool = False) -> None:
    \"\"\"Apply a clean tournament-board style to the dashboard with Light/Dark mode support.\"\"\"

    theme_class = "dark-theme" if dark_mode else "light-theme"

    st.markdown(
        f\"\"\"
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

        /* We inject a hidden div to trigger the :has selector above if dark mode is active */
        </style>
        {{ f'<div class="dark-theme-trigger" style="display:none;"></div>' if dark_mode else '' }}
        <style>
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
            max-width: 150px;
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
        \"\"\",
        unsafe_allow_html=True,
    )
'''

# We need to replace the old _inject_styles(st: Any) with the new one
old_def = r"def _inject_styles\(st: Any\) -> None:\n.*?def _local_flag_b64"
new_content = re.sub(old_def, new_inject_styles + "\n\n\ndef _local_flag_b64", content, flags=re.DOTALL)

with open('src/visualization/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

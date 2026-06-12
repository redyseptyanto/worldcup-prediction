import re

with open('src/visualization/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

modal_code = '''
def show_match_analysis_modal(home: str, away: str):
    import streamlit as st
    @st.cache_resource
    def get_cached_model():
        from src.models.train import load_or_train_ensemble
        return load_or_train_ensemble()
        
    model = get_cached_model()
    
    @st.dialog(f"Match Analysis", width="large")
    def _modal():
        st.markdown(f"### {_local_flag_html(home)} {home} vs {_local_flag_html(away)} {away}", unsafe_allow_html=True)
        st.write(f"**Prediction Details**")
        
        prediction = model.predict_match(home, away)
        probs = prediction["outcome_probabilities"]
        score = prediction["predicted_score"]
        
        st.write(f"**Predicted Score**: {home} {score['home']} - {score['away']} {away}")
        st.write(f"**Win Probabilities**: {home} ({probs['home_win']:.1%}) | Draw ({probs['draw']:.1%}) | {away} ({probs['away_win']:.1%})")
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
                
            from src.features.team_features import get_head_to_head
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
            import pandas as pd
            if ROSTERS_FILE.exists():
                rosters = pd.read_csv(ROSTERS_FILE)
                
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

'''

# We will inject this right before "def main() -> None:"
insert_pattern = r'(def main\(\) -> None:)'
content = re.sub(insert_pattern, modal_code + '\n\n' + r'\1', content, count=1)

with open('src/visualization/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

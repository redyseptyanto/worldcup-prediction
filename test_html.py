import streamlit as st
import base64

with open("data/raw/flags/Argentina.png", "rb") as f:
    data = base64.b64encode(f.read()).decode()

html = f"""
<div class="champion-card">
    <div class="champion-trophy"><img src="data:image/png;base64,{data}" /></div>
    <div class="champion-label">Projected Champion</div>
</div>
"""
st.markdown(html, unsafe_allow_html=True)

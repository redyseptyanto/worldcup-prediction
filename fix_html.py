import re

with open("src/visualization/dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace st.markdown(..., unsafe_allow_html=True)
# We will just import re and define _render_html
helper = """
def _render_html(st, html_str: str) -> None:
    import re
    st.markdown(re.sub(r'\\n\\s+', '\\n', html_str), unsafe_allow_html=True)
"""

if "_render_html(st, html_str:" not in content:
    # Insert helper after imports
    content = content.replace("from src.config import FLAGS_DIR\n", "from src.config import FLAGS_DIR\n" + helper + "\n")

# Now replace st.markdown( string, unsafe_allow_html=True)
# This is tricky with regex because of multiline.
# Let's just use string replace for the specific blocks.

blocks_to_replace = [
    ('st.markdown(\n        f"""\n        <div class="group-card">', '_render_html(\n        st,\n        f"""\n        <div class="group-card">'),
    ('st.markdown(\n        f"""\n        <div class="match-card">', '_render_html(\n        st,\n        f"""\n        <div class="match-card">'),
    ('st.markdown(\n        """\n        <div class="overview-shell">', '_render_html(\n        st,\n        """\n        <div class="overview-shell">'),
    ('st.markdown(\n            f"""\n            <div class="champion-card">', '_render_html(\n            st,\n            f"""\n            <div class="champion-card">'),
    ('st.markdown(\'<div class="knockout-shell"><div class="knockout-title">Knockout Picture</div></div>\', unsafe_allow_html=True)', '_render_html(st, \'<div class="knockout-shell"><div class="knockout-title">Knockout Picture</div></div>\')'),
    ('st.markdown(\n            f\'<div class="snapshots-note">Snapshots loaded: {", ".join(snapshots)}</div>\',\n            unsafe_allow_html=True,\n        )', '_render_html(st, f\'<div class="snapshots-note">Snapshots loaded: {", ".join(snapshots)}</div>\')')
]

for old, new in blocks_to_replace:
    content = content.replace(old, new)

# Wait, we need to remove the trailing unsafe_allow_html=True for the f""" blocks
content = re.sub(r'</div>\s*""",\s*unsafe_allow_html=True,\s*\)', '</div>\n        """)', content)
content = re.sub(r'</div>\n            """,\n            unsafe_allow_html=True,\n        \)', '</div>\n            """)', content)

with open("src/visualization/dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)

print("done")

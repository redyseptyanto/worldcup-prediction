import re

with open('src/visualization/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The match_analysis_modal is inside _render_predictions_tab
# Let's extract everything from "@st.cache_resource" to the end of the modal definition.
# It ends right before "with accuracy_tab:" or the end of the predictions tab block.
# Actually, the modal function is indented by 16 spaces.

pattern = r'''(                @st\.cache_resource\s*
                def get_cached_model\(\):\s*
                    from src\.models\.train import load_or_train_ensemble\s*
                    return load_or_train_ensemble\(\)\s*
                    \s*
                model = get_cached_model\(\)\s*
                \s*
                @st\.dialog\([^)]+\)\s*
                def match_analysis_modal\(\):.*?)(?=\n    with accuracy_tab:|\n    with compare_tab:)'''

match = re.search(pattern, content, flags=re.DOTALL)
if match:
    old_block = match.group(1)
    
    # We want to unindent old_block by 16 spaces
    lines = old_block.split('\n')
    unindented_lines = []
    for line in lines:
        if line.startswith('                '):
            unindented_lines.append(line[16:])
        else:
            unindented_lines.append(line)
            
    # Modify the signature to take home and away
    new_modal = '\n'.join(unindented_lines)
    new_modal = new_modal.replace('def match_analysis_modal():', 'def show_match_analysis_modal(home: str, away: str):')
    
    # Remove the old block from the content
    new_content = content.replace(old_block, '                show_match_analysis_modal(home, away)\n')
    
    # Insert new_modal right before _render_predictions_tab() or somewhere at top level
    insert_pattern = r'(def _render_predictions_tab\(\) -> None:)'
    new_content = re.sub(insert_pattern, new_modal + '\n\n' + r'\1', new_content, count=1)
    
    with open('src/visualization/dashboard.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully extracted show_match_analysis_modal")
else:
    print("Could not find the modal block")

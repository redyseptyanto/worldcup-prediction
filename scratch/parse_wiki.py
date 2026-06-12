import re

with open(r'C:\Users\PSA-Airbyte\.gemini\antigravity-ide\brain\dd20ae68-fb76-4621-a4a8-02e2909dccfa\.system_generated\steps\1309\content.md', 'r', encoding='utf-8') as f:
    html = f.read()

parts = re.split(r'(Match 7[3-9]|Match 8[0-8])', html)
for i in range(1, len(parts), 2):
    chunk = parts[i] + parts[i+1][:500]
    teams = re.findall(r'(Winner Group [A-L]|Runner-up Group [A-L]|3rd Group [A-L/]+)', chunk)
    if len(teams) >= 2:
        print(f'{parts[i]}: {teams[0]} vs {teams[1]}')

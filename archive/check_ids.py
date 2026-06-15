import re

with open('FRONTEND/recommendation.html', encoding='utf-8') as f:
    html = f.read()

with open('FRONTEND/recommendation.js', encoding='utf-8') as f:
    js = f.read()

ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js))
missing = [i for i in ids if f'id="{i}"' not in html]

print("Missing IDs:", missing)

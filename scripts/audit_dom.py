import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

with open('static/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

js_ids = set(re.findall(r'getElementById\([\'"]([a-zA-Z0-9_-]+)[\'"]\)', js_content))
html_ids = set(re.findall(r'id=[\'"]([a-zA-Z0-9_-]+)[\'"]', html_content))

missing = js_ids - html_ids
# Exclude dynamically rendered element IDs in app.js
dynamic_elements = [
    'upcoming-pipeline-count-badge', 'upcoming-pipeline-table-container',
    'rescheduled-count-badge', 'rescheduled-table-container',
    'badge-active-tab-count', 'badge-upcoming-tab-count', 'badge-awaiting-tab-count',
    'badge-disposed-tab-count', 'badge-all-tab-count', 'court-chips-row',
    'hearing-board-list-container', 'all-cases-tbody', 'clients-tbody',
    'wa-dockets-tbody', 'leads-tbody', 'calendar-grid'
]

unmatched = [i for i in missing if i not in html_ids]
print(f"Total getElementById calls: {len(js_ids)}")
print(f"Total defined HTML IDs: {len(html_ids)}")
print(f"Missing DOM IDs: {unmatched}")

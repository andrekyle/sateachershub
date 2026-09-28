"""Render current Section B (Q4-Q8) and dump heading + marks structure,
plus extract any embedded images from PDF pages 12-13 (Q8 figures).
"""
import re
import app

c = app.app.test_client()
with c.session_transaction() as s:
    s['user_id'] = '951c278b-2d76-4969-b0d4-6271479bf397'
    s['_user_id'] = '951c278b-2d76-4969-b0d4-6271479bf397'
    s['user_role'] = 'teacher'

html = c.get('/teacher/generator/18cc87c0-2ee3-43fe-b74c-89aa56a3ad71/preview?pages=20').get_data(as_text=True)

for qn in ['QUESTION 4', 'QUESTION 5', 'QUESTION 6', 'QUESTION 7', 'QUESTION 8']:
    i = html.find(qn)
    seg = re.sub('<[^>]+>', ' ', html[i:i+120])
    seg = re.sub(r'\s+', ' ', seg)
    print(f'{qn!r:14} -> {seg.strip()[:90]}')

# group totals [N]
print('\nq-total markers:', re.findall(r'\[(\d+)\]', re.sub('<[^>]+>', ' ', html)))

import re
import app

c = app.app.test_client()
with c.session_transaction() as s:
    s['user_id'] = '951c278b-2d76-4969-b0d4-6271479bf397'
    s['_user_id'] = '951c278b-2d76-4969-b0d4-6271479bf397'
    s['user_role'] = 'teacher'

r = c.get('/teacher/generator/18cc87c0-2ee3-43fe-b74c-89aa56a3ad71/preview?pages=20')
print('status', r.status_code)
html = r.get_data(as_text=True)
i = html.find('7369fb99-76bc-4edb-8782-b9f3bb81d477')
print('idx', i)
if i > 0:
    snip = html[i - 120:i + 1100]
    snip = re.sub(r'\s+', ' ', snip)
    print(snip)

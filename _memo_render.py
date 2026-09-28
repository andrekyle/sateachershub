import re
from app import app

PID = "06a40eac-5b21-4ef1-815c-698cecce89f2"
app.config['TESTING'] = True
c = app.test_client()
UID = '951c278b-2d76-4969-b0d4-6271479bf397'
with c.session_transaction() as s:
    s['user_id'] = UID
    s['user_role'] = 'teacher'
    s['_user_id'] = UID
# try memo route
r = c.get(f"/teacher/generator/{PID}/memo")
print("status", r.status_code)
html = r.get_data(as_text=True)
# rewrite /static/ to file:// absolute
import os
base = os.path.abspath('.').replace('\\','/')
html = html.replace('/static/', f'file:///{base}/static/')
html = html.replace('url_for', 'url_for')  # noop
open("_memo_render.html", "w", encoding="utf-8").write(html)
print("written _memo_render.html len", len(html))

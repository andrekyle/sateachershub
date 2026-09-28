import os, sys
from app import app

PID = "7887deb7-9b51-4927-96ee-6b937d3ca401"
app.config['TESTING'] = True
c = app.test_client()
UID = '951c278b-2d76-4969-b0d4-6271479bf397'
with c.session_transaction() as s:
    s['user_id'] = UID
    s['user_role'] = 'teacher'
    s['_user_id'] = UID

memo = len(sys.argv) > 1 and sys.argv[1] == 'memo'
url = f"/teacher/generator/{PID}/memo" if memo else f"/teacher/generator/{PID}/preview"
r = c.get(url)
print("status", r.status_code)
html = r.get_data(as_text=True)
base = os.path.abspath('.').replace('\\', '/')
html = html.replace('/static/', f'file:///{base}/static/')
out = "_p2mj23_memo.html" if memo else "_p2mj23_paper.html"
open(out, "w", encoding="utf-8").write(html)
print("written", out, "len", len(html))

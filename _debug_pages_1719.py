import io
import pdfplumber
import requests
from app import app, GeneratedPaper, db

PID = '59936ea1-87fc-4507-8f15-4c4c77e22dfd'

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    owner_id = p.owner_id

client = app.test_client()
with client.session_transaction() as sess:
    sess['_user_id'] = owner_id
    sess['_fresh'] = True

ck = client.get_cookie('session').value
url = f'http://127.0.0.1:5004/teacher/generator/{PID}/memo/pdf'
resp = requests.get(url, cookies={'session': ck}, timeout=120)
print('status', resp.status_code, 'bytes', len(resp.content))
if resp.status_code != 200:
    print(resp.text)
    raise SystemExit(1)

pdf = pdfplumber.open(io.BytesIO(resp.content))
print('pages', len(pdf.pages))
for n in [17, 18, 19]:
    if 1 <= n <= len(pdf.pages):
        out = f'_memo_now_p{n}.png'
        pdf.pages[n-1].to_image(resolution=150).save(out)
        t = (pdf.pages[n-1].extract_text() or '')[:300].replace('\n', ' | ')
        print('saved', out, 'text:', t)
pdf.close()

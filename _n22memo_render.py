from app import app
PID = "49670bf2-0dbd-45c0-a6c1-547fa8091675"
UID = "951c278b-2d76-4969-b0d4-6271479bf397"
with app.test_client() as c:
    with c.session_transaction() as s:
        s['user_id'] = UID; s['user_role'] = 'teacher'; s['_user_id'] = UID
    html = c.get(f"/teacher/generator/{PID}/memo").get_data(as_text=True)
body = html.split('</style>')[-1]
import re
i = body.find('TRUE/FALSE')
seg = body[i-400:i+3200] if i>=0 else 'TF not found'
# strip tags for readability
txt = re.sub(r'<[^>]+>', ' ', seg)
txt = re.sub(r'\s+', ' ', txt)
print(txt.encode('ascii','replace').decode('ascii'))
print("=== checks ===")
print("Note to marker present:", 'Note to marker' in body)
k = body.find('Note to marker')
seg3 = body[k-100:k+500] if k>=0 else ''
print("NOTE raw:", re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ', seg3)).encode('ascii','replace').decode('ascii'))

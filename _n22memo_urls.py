from app import app
PID = "49670bf2-0dbd-45c0-a6c1-547fa8091675"
UID = "951c278b-2d76-4969-b0d4-6271479bf397"
with app.test_client() as c:
    with c.session_transaction() as s:
        s['user_id'] = UID; s['user_role'] = 'teacher'; s['_user_id'] = UID
    # try memo/answer preview
    for url in [f"/teacher/generator/{PID}/preview?memo=1",
                f"/teacher/generator/{PID}/memo",
                f"/teacher/generator/{PID}/preview"]:
        r = c.get(url)
        print(url, '->', r.status_code)

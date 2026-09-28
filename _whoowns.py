from app import app, db, GeneratedPaper, User
PID = "06a40eac-5b21-4ef1-815c-698cecce89f2"
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    print("owner_id", p.owner_id)
    u = db.session.get(User, p.owner_id)
    print("user", u.id, getattr(u,'role',None), getattr(u,'email',None))

from app import app, db, GeneratedPaper, _build_paper_context
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    ctx = _build_paper_context(p, with_memo=False, version='current')
    secs = ctx.get('sections') or []
    for si, sec in enumerate(secs):
        print(f'SEC {si} title={sec.get("title")!r} marks={sec.get("marks")!r}')
        for gi, g in enumerate(sec.get('qgroups') or []):
            print(f'   Q{g.get("qn")} marks={g.get("marks")!r}')

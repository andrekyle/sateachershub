import app as appmod
PID = "60471f83-d846-48f7-9195-629c43e3ab8f"
with appmod.app.app_context():
    p = appmod.GeneratedPaper.query.get(PID)
    for f in ['instructions','cover_note','cover_text','header_left','header_right','footer_left','footer_right','total_marks','paper_number','title','subject']:
        v = getattr(p, f, '__none__')
        print(f"{f} = {v!r}")

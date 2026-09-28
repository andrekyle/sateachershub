from app import app, GeneratedPaper
with app.app_context():
    for p in GeneratedPaper.query.all():
        t = (p.title or '')
        print(p.id, '|', t, '| pn=', p.paper_number, '| date=', p.exam_date, '| total=', p.total_marks)

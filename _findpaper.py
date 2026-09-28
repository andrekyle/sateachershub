from app import app, db, GeneratedPaper
with app.app_context():
    papers = GeneratedPaper.query.filter(GeneratedPaper.title.like('%P2%')).all()
    for p in papers:
        print(p.id, '|', p.title, '| num', p.paper_number, '| marks', p.total_marks, '| date', p.exam_date)
    print('---- ALL with 2023 ----')
    for p in GeneratedPaper.query.all():
        t=(p.title or '')
        if '2023' in t or (p.exam_date and p.exam_date.year==2023):
            print(p.id, '|', t, '| num', p.paper_number, '| date', p.exam_date)

from app import app, db, GeneratedPaper

with app.app_context():
    papers = GeneratedPaper.query.all()
    print('TOTAL PAPERS:', len(papers))
    for p in papers:
        t = (p.title or '')
        if 'P1' in t or (getattr(p, 'paper_number', None) in (1, '1')):
            print('---')
            print('id:', p.id)
            print('title:', t)
            print('paper_number:', getattr(p, 'paper_number', None))
            print('subject:', getattr(p, 'subject', None))
            print('grade:', getattr(p, 'grade', None))
            print('exam_date:', getattr(p, 'exam_date', None))
            print('owner_id:', p.owner_id)
            print('total_marks:', getattr(p, 'total_marks', None))

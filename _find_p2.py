import json
from app import app, db, GeneratedPaper, QuestionBankItem

with app.app_context():
    papers = GeneratedPaper.query.all()
    for p in papers:
        t = (p.title or '')
        if 'P2' in t and ('2024' in t or (p.exam_date and p.exam_date.year==2024)):
            print(f"id={p.id}")
            print(f"  title={t!r}")
            print(f"  exam_date={p.exam_date} total_marks={p.total_marks} paper_number={getattr(p,'paper_number',None)}")
    print("\n--- ALL P2 papers ---")
    for p in papers:
        if 'P2' in (p.title or ''):
            print(f"{p.id}  {p.title!r}  {p.exam_date}")

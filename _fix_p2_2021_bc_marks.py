import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'

# (section_index, item_index_in_section, expected_current_mark, new_mark, label)
FIXES = [
    (1, 14, 25, 4, 'Q4 last item (leaked Q4 total)'),
    (1, 24, 15, 2, 'Q5 last item (leaked Q5 total)'),
    (1, 30, 10, 2, 'Q6 last item (leaked Q6 total)'),
    (1, 38, 10, 1, 'Q7 last item (leaked Q7 total)'),
    (1, 51, 1, 3, 'Q8.9 HTML diagram (undercounted, MG=3)'),
    (2, 19, 25, 2, 'Q9 last item (leaked Q9 total)'),
]

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    for si, ii, exp, new, label in FIXES:
        qid = secs[si]['question_ids'][ii]
        q = db.session.get(QuestionBankItem, qid)
        cur = q.marks
        flag = 'OK' if cur == exp else f'WARN expected {exp}'
        q.marks = new
        print(f'sec{si} idx{ii} id={qid[:8]} {cur}->{new}  [{flag}]  {label}')
    db.session.commit()

    # Recompute section totals
    for si, s in enumerate(secs):
        qids = s['question_ids']
        tot = sum((db.session.get(QuestionBankItem, x).marks or 0) for x in qids)
        print(f'  Section {si} ({s.get("title")}) total = {tot}')

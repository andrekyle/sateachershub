from app import app, db, QuestionBankItem, GeneratedPaper
import json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections) if isinstance(p.sections, str) else p.sections
    # Q7 is in Section B (Q5..Q8) — splits[3]=29, splits[4]=34 — items 29..33 = Q7.x? actually Q7 might span 29..30
    # Show all section B items with index
    for si, sec in enumerate(secs):
        print(f'\n=== SEC {si}: {sec.get("title","?")[:60]} splits={sec.get("splits")}')
        qids = sec.get('question_ids', [])
        for idx, qid in enumerate(qids):
            q = db.session.get(QuestionBankItem, qid)
            qt = (q.question_text or '')[:80].replace('\n',' ')
            print(f'  [{idx}] qid={qid} marks={q.marks} | {qt}')

from app import app, db, GeneratedPaper, QuestionBankItem
import json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections) if isinstance(p.sections, str) else p.sections
    secC = secs[2]
    qids = secC['question_ids']
    for i, qid in enumerate(qids):
        q = db.session.get(QuestionBankItem, qid)
        if not q: continue
        qt = (q.question_text or '').replace('\n', ' ')[:140]
        if '10.1.2' in qt or '10.1.2' in (q.answer_text or '')[:120]:
            print(f'[{i}] qid={qid}')
            print(f'    Q: {qt}')
            print(f'    marks={q.marks}')
            print(f'    A: {(q.answer_text or "")[:600]}')
            print('---')

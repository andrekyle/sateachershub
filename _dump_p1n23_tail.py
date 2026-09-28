import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    qids = secs[0]['question_ids']
    for i in (48, 49, 52):
        q = db.session.get(QuestionBankItem, qids[i])
        print(f"\n===== idx {i} (marks={q.marks}) =====")
        print(repr(q.question_text))

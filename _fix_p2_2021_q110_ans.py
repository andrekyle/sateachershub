from app import app, db, GeneratedPaper, QuestionBankItem
import json
PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
with app.app_context():
    p = GeneratedPaper.query.get(PID)
    qids = json.loads(p.sections)[0]['question_ids']
    q = db.session.get(QuestionBankItem, qids[9])
    print('BEFORE marks=', q.marks, 'ans=', repr(q.answer_text))
    q.answer_text = 'B'
    if not q.marks or q.marks != 1:
        q.marks = 1
    db.session.commit()
    q2 = db.session.get(QuestionBankItem, qids[9])
    print('AFTER  marks=', q2.marks, 'ans=', repr(q2.answer_text))

# -*- coding: utf-8 -*-
import json
from app import app, db, GeneratedPaper, QuestionBankItem
PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    sec = secs[0]
    qids = sec['question_ids']
    qpost = sec.get('qpost_texts') or {}
    for i in (41,):
        q = db.session.get(QuestionBankItem, qids[i])
        print(f"idx {i} id={qids[i]} marks={q.marks} img={q.image_path}")
        print("question_text =", repr(q.question_text))
        print("post_text =", repr(qpost.get(qids[i])))

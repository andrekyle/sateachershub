# -*- coding: utf-8 -*-
"""Move the CAT P1 Nov 2023 Q6.1 NOTE block below the image (into qpost_texts)."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
NEW_QTEXT = ("Open the incomplete 6_1Win file in a web browser and also in a text/HTML editor.\n\n"
             "Your final web page should look like the example below.")
NOTE_POST = ("NOTE:\n"
             "•  Use the example above as a guide when answering this question.\n"
             "•  Question numbers appear as comments in the coding to indicate where you "
             "should insert the answer(s). DO NOT delete these comments.")
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    sec = secs[0]
    qids = sec['question_ids']
    qid = qids[41]
    q = db.session.get(QuestionBankItem, qid)
    q.question_text = NEW_QTEXT
    qpost = sec.get('qpost_texts') or {}
    qpost[qid] = NOTE_POST
    sec['qpost_texts'] = qpost
    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    print("DONE")
    print("question_text =", repr(q.question_text))
    print("post_text =", repr(qpost[qid]))

# -*- coding: utf-8 -*-
"""Remove the 'noborder' tag from the 9 CAT P1 Nov 2023 example images so the
black figure border (like the original PDF) is applied."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
IDXS = [1, 4, 6, 18, 19, 30, 41, 47, 48]
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    qids = secs[0]['question_ids']
    for idx in IDXS:
        q = db.session.get(QuestionBankItem, qids[idx])
        tags = [t.strip() for t in (q.tags or '').split(',') if t.strip() and t.strip().lower() != 'noborder']
        q.tags = ', '.join(tags)
        print(f"idx {idx}: tags now = {q.tags!r}, img={q.image_path}")
    db.session.commit()
    print("DONE — noborder removed from", len(IDXS), "images")

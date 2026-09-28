# -*- coding: utf-8 -*-
import json, re
from app import app, db, GeneratedPaper, QuestionBankItem
PID = '2b687490-9157-4e10-b0c9-2bab1ee303fd'
BULLET = '\u2022'
HAS_MARK = re.compile(r'\s\d\s*$')          # " 1" style trailing mark (space+digit)
# bullets worth 2 marks in Q1-Q4 (idx5 = 1.6 multilevel indents)
TWO = ('Aligned at 0 cm', 'Aligned at 1 cm')

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    qids = json.loads(p.sections)[0]['question_ids']
    changed = 0
    for i in range(0, 33):
        q = db.session.get(QuestionBankItem, qids[i])
        at = q.answer_text or ''
        if not at:
            continue
        out = []
        for ln in at.split('\n'):
            s = ln.rstrip()
            # drop leaked general-instruction chrome bullets (idx9 1.10)
            low = s.lower()
            if 'check the accuracy and skill' in low or 'ignore spelling in all cases' in low:
                continue
            if s.lstrip().startswith(BULLET) and not HAS_MARK.search(s):
                mark = 2 if any(t in s for t in TWO) else 1
                s = s + '  ' + str(mark)
            out.append(s)
        new = '\n'.join(out).rstrip()
        if new != at:
            q.answer_text = new
            changed += 1
    db.session.commit()
    print('items changed:', changed)

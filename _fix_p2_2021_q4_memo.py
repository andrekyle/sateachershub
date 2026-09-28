# -*- coding: utf-8 -*-
from app import app, db, GeneratedPaper, QuestionBankItem
import json

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
TICK = '\u2713'

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    qids = json.loads(p.sections)[1]['question_ids']

    # idx1 = 4.2 : rejoin wrapped reason lines, explicit tick at each reason end
    a42 = (
        'TWO reasons for an entry level CPU\n'
        '(1) An entry level CPU has enough processing power for a computer used in a SOHO ' + TICK + '\n'
        '(2) It would be an unnecessary expense to get a more powerful CPU that is used to capacity ' + TICK
    )
    # idx5 = 4.4.2 : tick after "etc." (before the Accept note)
    a442 = (
        'A system utility used to remove unwanted files\n'
        'Disk Cleanup/CCleaner, etc. ' + TICK + ' (Accept any other valid response)'
    )
    # idx14 = 4.10 : add missing Reason tick after "desktop"
    a410 = (
        'Reason for not successfully saving with Send to and solution\n'
        'Reason:\n'
        'This action will only create a shortcut, and not save the actual file to desktop ' + TICK + '\n'
        'Solution:\n'
        '(1) Copy and paste to the desktop\n'
        "(2) Open the document and save it to the desktop ('File Save As')\n"
        '(3) Click and drag to the Desktop if already saved elsewhere\n'
        '(Any one)'
    )

    edits = {qids[1]: a42, qids[5]: a442, qids[14]: a410}
    for qid, new in edits.items():
        q = db.session.get(QuestionBankItem, qid)
        print('BEFORE', qid[:8], repr((q.answer_text or '')[:80]))
        q.answer_text = new
    db.session.commit()
    for qid in edits:
        q = db.session.get(QuestionBankItem, qid)
        print('AFTER ', qid[:8], repr(q.answer_text))

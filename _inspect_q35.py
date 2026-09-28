"""Inspect Q3.5 (Section A) for leftover boilerplate in its question_text."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

with app.app_context():
    paper = db.session.get(GeneratedPaper, PAPER_ID)
    secs = json.loads(paper.sections)
    secA = secs[0]
    qids = secA.get('question_ids', [])
    print('Section A splits:', secA.get('splits'))
    # Q3 is the third group; print the last few items
    for i in range(20, len(qids)):
        it = db.session.get(QuestionBankItem, qids[i])
        if not it:
            continue
        print('[idx %d] id=%s marks=%s' % (i, qids[i], it.marks))
        print('   text=%r' % (it.question_text or ''))
        print('-' * 40)

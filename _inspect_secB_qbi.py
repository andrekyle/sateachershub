"""Inspect QuestionBankItem records for Section B idx0 (4.1) and idx43 (8.4)."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = p.sections if isinstance(p.sections, list) else json.loads(p.sections)
    secB = secs[1]
    qids = secB['question_ids']
    print('num qids:', len(qids))
    for idx in (0, 43, 45):
        qid = qids[idx]
        it = db.session.get(QuestionBankItem, qid)
        print('\n===== idx', idx, 'qid', qid, '=====')
        print('question_text:', repr((it.question_text or '')[:300]))
        print('marks:', it.marks, '| type:', it.question_type)
        print('image_path:', repr(it.image_path))
        print('image_width:', getattr(it, 'image_width', None), '| image_offset:', getattr(it, 'image_offset', None))

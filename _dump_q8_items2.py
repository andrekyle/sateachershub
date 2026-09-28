"""Dump Section B keys and its Q8 items (from QuestionBankItem) for P2 2025."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

with app.app_context():
    paper = db.session.get(GeneratedPaper, PAPER_ID)
    secs = json.loads(paper.sections)
    secB = secs[1]
    print('SECTION B keys:', list(secB.keys()))
    print('title:', secB.get('title'))
    print('splits:', secB.get('splits'))
    print('qtitles:', secB.get('qtitles'))
    qpt = secB.get('qpost_texts')
    print('qpost_texts type:', type(qpt))
    if isinstance(qpt, dict):
        for k, v in qpt.items():
            print('  qpt[%s] = %r' % (k, (v or '')[:120]))
    elif isinstance(qpt, list):
        for i, v in enumerate(qpt):
            if v:
                print('  qpt[%d] = %r' % (i, (v or '')[:120]))
    qids = secB.get('question_ids', [])
    print('num question_ids:', len(qids))
    print('=' * 60)
    for i in range(40, len(qids)):
        qid = qids[i]
        item = db.session.get(QuestionBankItem, qid)
        if not item:
            print('[idx %d] id=%s MISSING' % (i, qid))
            continue
        txt = (item.question_text or '').replace('\n', ' \\n ')
        print('[idx %d] id=%s' % (i, qid))
        print('   marks=%s type=%s img=%r w=%s' % (item.marks, item.question_type, item.image_path, item.image_width))
        print('   text=%s' % txt[:300])
        print('-' * 40)

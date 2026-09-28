"""Dump current Section B (Q4-Q7) of the live CAT P2 May-June 2025 paper."""
import json
import app
from app import GeneratedPaper, QuestionBankItem

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

out = []
with app.app.app_context():
    p = GeneratedPaper.query.get(PAPER_ID)
    secs = json.loads(p.sections)
    s = secs[1]  # Section B
    out.append('SECTION B keys: ' + ', '.join(s.keys()))
    out.append('title=' + repr(s.get('title')))
    out.append('splits=' + repr(s.get('splits')))
    out.append('subitems=' + repr(s.get('subitems')))
    out.append('qtitles=' + repr(s.get('qtitles')))
    out.append('qinstructions=' + repr(s.get('qinstructions')))
    qids = s['question_ids']
    out.append('n qids=' + str(len(qids)))
    items = {q.id: q for q in QuestionBankItem.query.filter(QuestionBankItem.id.in_(qids)).all()}
    splits = s['splits']
    for i, qid in enumerate(qids):
        q = items.get(qid)
        marker = ''
        if i in splits:
            marker = f'  <<< SPLIT (group {splits.index(i)})'
        out.append(f'\n--- idx {i} | qid {qid} | marks={q.marks} | type={q.question_type} | img={q.image_path!r}{marker}')
        out.append('  Q: ' + repr(q.question_text))
        out.append('  A: ' + repr(q.answer_text))

with open('_p2_2025_secB_db.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('wrote _p2_2025_secB_db.txt;', len(qids), 'items')

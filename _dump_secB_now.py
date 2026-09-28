"""Dump current Section B (Q4-Q8) from the P2 2025 paper DB record."""
import json
import app
from app import GeneratedPaper, QuestionBankItem

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

with app.app.app_context():
    p = GeneratedPaper.query.get(PAPER_ID)
    secs = json.loads(p.sections)
    s = secs[1]  # Section B
    qids = s['question_ids']
    splits = s['splits']
    subitems = s.get('subitems')
    print('SECTION B title=', s.get('title'))
    print('splits=', splits)
    print('subitems=', subitems)
    print('qtitles=', s.get('qtitles'))
    print('qinstructions=', json.dumps(s.get('qinstructions'), ensure_ascii=False))
    print('qpost_texts keys=', list((s.get('qpost_texts') or {}).keys()))
    print('nqids=', len(qids))
    items = {q.id: q for q in QuestionBankItem.query.filter(QuestionBankItem.id.in_(qids)).all()}
    lines = []
    for i, qid in enumerate(qids):
        q = items.get(qid)
        marker = ''
        if i in splits:
            marker += f' <<SPLIT idx{splits.index(i)}>>'
        if subitems and i in subitems:
            marker += ' <<SUBITEM>>'
        lines.append(f'--- idx {i}{marker} | qid={qid} | m={q.marks} | type={q.question_type} | img={q.image_path!r}')
        lines.append('    Q: ' + repr((q.question_text or '')))
        lines.append('    A: ' + repr((q.answer_text or ''))[:200])
        pt = (s.get('qpost_texts') or {}).get(qid)
        if pt:
            lines.append('    POST: ' + repr(pt))
    with open('_secB_dump.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('Wrote _secB_dump.txt with', len(qids), 'items')

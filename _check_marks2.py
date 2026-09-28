from app import app, db, QuestionBankItem
import sqlite3, json
with app.app_context():
    c = sqlite3.connect('instance/brandcartel.db')
    row = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
    secs = json.loads(row[0])
    secC = secs[2]
    qids = secC['question_ids']
    si = secC.get('subitems') or []
    print('subitems type:', type(si).__name__, 'len:', len(si) if hasattr(si,'__len__') else '?')
    if isinstance(si, list):
        print('subitems[20]:', si[20] if len(si) > 20 else None)
        print('subitems[12]:', si[12] if len(si) > 12 else None)
    elif isinstance(si, dict):
        print('subitems for q20:', si.get(qids[20]))
        print('subitems for q12:', si.get(qids[12]))
    splits = secC.get('splits') or [0]
    boundaries = splits + [len(qids)]
    for gi in range(len(splits)):
        lo, hi = boundaries[gi], boundaries[gi+1]
        total = 0
        per = []
        for j in range(lo, hi):
            q = db.session.get(QuestionBankItem, qids[j])
            m = int(q.marks or 0)
            total += m
            per.append((j, m, (q.question_text or '')[:60].replace('\n',' ')))
        print(f'--- Group {gi} items {lo}-{hi-1} total={total}')
        for row in per:
            print('  ', row)
    q20 = db.session.get(QuestionBankItem, qids[20])
    print('FULL Q20 marks=', q20.marks)
    print(repr(q20.question_text))
    q12 = db.session.get(QuestionBankItem, qids[12])
    print('FULL Q12 marks=', q12.marks)
    print(repr(q12.question_text))

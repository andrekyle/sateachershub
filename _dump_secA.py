from app import app, db, QuestionBankItem
import sqlite3, json
with app.app_context():
    c = sqlite3.connect('instance/brandcartel.db')
    row = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
    secs = json.loads(row[0])
    secA = secs[0]
    print('SECTION A keys:', list(secA.keys()))
    print('splits:', secA.get('splits'))
    print('qtitles:', secA.get('qtitles'))
    print('qinstructions:', secA.get('qinstructions'))
    qids = secA['question_ids']
    for i, qid in enumerate(qids):
        q = db.session.get(QuestionBankItem, qid)
        if q is None:
            print(i, qid, 'MISSING'); continue
        print(i, qid, 'type=', q.question_type, 'marks=', q.marks)
        print('  Q:', repr((q.question_text or '')[:120]))
        print('  A:', repr((q.answer_text or '')[:120]))

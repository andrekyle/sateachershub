from app import app, db, QuestionBankItem
import sqlite3, json
with app.app_context():
    c = sqlite3.connect('instance/brandcartel.db')
    row = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
    secs = json.loads(row[0])
    secB = secs[1]
    print('SECTION B keys:', list(secB.keys()))
    print('splits:', secB.get('splits'))
    print('qtitles:', secB.get('qtitles'))
    qids = secB['question_ids']
    print('len qids:', len(qids))
    for i, qid in enumerate(qids):
        q = db.session.get(QuestionBankItem, qid)
        if q is None:
            print(i, qid, 'MISSING'); continue
        print(i, qid, 'm=', q.marks)
        print('   Q:', repr((q.question_text or '')[:200]))
        print('   A:', repr((q.answer_text or '')[:300]))

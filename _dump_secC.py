import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
row = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(row[0])
secC = secs[2]
qids = secC['question_ids']
print('total qids in section C:', len(qids))
# Find Q10 boundaries via splits if present
print('splits:', secC.get('splits'))
print('qtitles:', secC.get('qtitles'))
# print last ~12 question items
from app import app, db, QuestionBankItem
with app.app_context():
    for i, qid in enumerate(qids):
        q = QuestionBankItem.query.get(qid)
        if q is None:
            print(i, qid, 'MISSING')
            continue
        print(i, qid, 'marks=', q.marks, 'text=', (q.question_text or '')[:120].replace('\n',' / '))

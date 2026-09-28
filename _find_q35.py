import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
sec0 = secs[0]
qids = sec0['question_ids']
print('Total Section A items:', len(qids))
for j in range(20, 25):
    qid = qids[j]
    cur.execute("SELECT question_type, marks, question_text, answer_text FROM question_bank_items WHERE id=?", (qid,))
    r = cur.fetchone()
    print('=' * 60, f'item {j} -> 3.{j-19}')
    print('  qid:', qid, 'type:', r[0], 'marks:', r[1])
    print('  qt:', repr(r[2]))
    print('  at:', repr(r[3]))

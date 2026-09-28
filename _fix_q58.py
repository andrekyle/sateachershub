import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
qid = None
r = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(r[0])
qid = secs[1]['question_ids'][23]
print("qid=", qid)
row = c.execute("select id, question_text, marks from question_bank_items where id=?", (qid,)).fetchone()
print("Before: marks=", row[2])
print("Text:", row[1])
c.execute("update question_bank_items set marks=? where id=?", (2, qid))
c.commit()
row = c.execute("select marks from question_bank_items where id=?", (qid,)).fetchone()
print("After: marks=", row[0])

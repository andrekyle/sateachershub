import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE title='CAT P2 Nov 2023'")
sections = json.loads(cur.fetchone()[0])
sa = sections[0]
qids = sa['question_ids']
splits = sa['splits']  # [0,10,20]
# Q2 matching group = qids[10:20]
q2 = qids[splits[1]:splits[2]]
print('Q2 count =', len(q2))
# Inspect first matching item to see column B options
for qid in q2[:2]:
    cur.execute("SELECT question_type, question_text, answer_text FROM question_bank_items WHERE id=?", (qid,))
    t, qt, at = cur.fetchone()
    print('\n--- type=', t, '---')
    print('Q:', (qt or '')[:600])
    print('A:', (at or '')[:120])
# Q1 first item
q1 = qids[splits[0]:splits[1]]
print('\n\nQ1 count =', len(q1))
cur.execute("SELECT question_text, answer_text FROM question_bank_items WHERE id=?", (q1[0],))
qt, at = cur.fetchone()
print('Q1.1 Q:', (qt or '')[:300])
print('Q1.1 A:', at)

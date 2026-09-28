import sqlite3, json
# Compare Nov 2023 P2 Q2 matching
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT id, sections FROM generated_papers WHERE title='CAT P2 Nov 2023'")
pid, secs_json = cur.fetchone()
sections = json.loads(secs_json)
print('=== Nov 2023 P2 ===')
for i, s in enumerate(sections):
    print(f"Sec {i}: {s.get('title')} splits={s.get('splits')} qtitles={s.get('qtitles')} #qids={len(s.get('question_ids',[]))}")
# Section A Q2 likely matching - get the chunk after split[1]
sa = sections[0]
splits = sa['splits']
qids = sa['question_ids']
q2 = qids[splits[1]:splits[2]]
print('\nQ2 qids:', q2)
for qid in q2[:3]:
    cur.execute("SELECT question_type, marks, question_text, answer_text FROM question_bank_items WHERE id=?", (qid,))
    row = cur.fetchone()
    print('type=', row[0], 'marks=', row[1])
    print('Q:', (row[2] or '')[:400])
    print('A:', (row[3] or '')[:200])
    print()


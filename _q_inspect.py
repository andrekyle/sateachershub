import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
c.row_factory = sqlite3.Row

paper = c.execute("SELECT sections FROM generated_papers WHERE id='48c8c8d1-b356-490a-90a6-56868b67d10d'").fetchone()
secs = json.loads(paper['sections'])
print('SECTIONS:', len(secs))
for s in secs:
    print(' title=', s.get('title'), 'qcount=', len(s.get('question_ids', [])))

# Q1 first id
qid = secs[0]['question_ids'][0]
r = c.execute("SELECT id, topic, subtopic, question_type, marks, question_text, tags FROM question_bank_items WHERE id=?", (qid,)).fetchone()
print('\nQ1 row:')
for k in r.keys():
    v = r[k]
    print(f'  {k} = {str(v)[:400]}')

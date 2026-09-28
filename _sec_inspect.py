import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("SELECT sections FROM generated_papers WHERE id='48c8c8d1-b356-490a-90a6-56868b67d10d'").fetchone()
sec = json.loads(r[0])[0]
print('keys:', list(sec.keys()))
print('splits:', sec.get('splits'))
print('qtitles:', sec.get('qtitles'))
print('qinstructions:', sec.get('qinstructions'))
print('subitems first 10:', (sec.get('subitems') or [])[:10])
print('total qids:', len(sec.get('question_ids') or []))
# show subtopic per qid to find question boundaries
for i, qid in enumerate(sec['question_ids']):
    row = c.execute("SELECT subtopic, marks FROM question_bank_items WHERE id=?", (qid,)).fetchone()
    print(i, row[0], 'm=', row[1])

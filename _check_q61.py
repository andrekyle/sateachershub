import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("SELECT question_text FROM question_bank_items WHERE id='93ef504a-d10e-4a6d-a141-35985cd16340'").fetchone()
print('Q6.1 question_text:')
print(repr(r[0]))
print('---')
s = c.execute("SELECT sections FROM generated_papers WHERE id='48c8c8d1-b356-490a-90a6-56868b67d10d'").fetchone()[0]
sec = json.loads(s)
print('qpost_texts on section[0]:')
print(sec[0].get('qpost_texts'))

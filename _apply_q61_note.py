import sqlite3, json

NOTE = ('**NOTE:**\n'
        '• Use the example on the previous page as a guideline when answering this question.\n'
        '• Question numbers appear as comments in the coding to indicate where you should insert the answer(s). Do NOT delete these comments.')

NEW_Q61 = ('Open the incomplete 6_1Home file in a web browser and also in a text/HTML editor (NOT a word processing program such as Word).\n\n'
           'Your final web page should look like the example below.')

QID_61 = '93ef504a-d10e-4a6d-a141-35985cd16340'
PAPER = '48c8c8d1-b356-490a-90a6-56868b67d10d'

c = sqlite3.connect('instance/brandcartel.db')
c.execute("UPDATE question_bank_items SET question_text=? WHERE id=?", (NEW_Q61, QID_61))

s = c.execute("SELECT sections FROM generated_papers WHERE id=?", (PAPER,)).fetchone()[0]
sec = json.loads(s)
qpt = sec[0].get('qpost_texts') or {}
qpt[QID_61] = NOTE
sec[0]['qpost_texts'] = qpt
c.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(sec), PAPER))
c.commit()
print('OK. Q6.1 stripped, qpost_texts set:', list(qpt.keys()))

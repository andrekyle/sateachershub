import sqlite3, json

QID_62 = '38987763-0e3f-4f5e-ad1f-623448851b85'
PAPER = '48c8c8d1-b356-490a-90a6-56868b67d10d'

NEW_Q62 = ('Open the incomplete 6_2Popular file in a web browser and also in a text/HTML editor (NOT a word processing program such as Word).\n\n'
           'Your final web page should look like the example below.')

POST_62 = ('Save and close the 6_2Popular file. (5)\n\n'
           'ONE mark will be allocated for closing tags and correct nesting in both web pages. (1)')

c = sqlite3.connect('instance/brandcartel.db')
c.execute("UPDATE question_bank_items SET question_text=?, image_path=? WHERE id=?",
          (NEW_Q62, 'uploads/cat_p1_n25/q6_2.png', QID_62))

s = c.execute("SELECT sections FROM generated_papers WHERE id=?", (PAPER,)).fetchone()[0]
sec = json.loads(s)
qpt = sec[0].get('qpost_texts') or {}
qpt[QID_62] = POST_62
sec[0]['qpost_texts'] = qpt
c.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(sec), PAPER))
c.commit()
print('OK. qpost_texts keys:', list(qpt.keys()))

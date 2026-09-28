import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT id, question_text FROM question_bank_items WHERE question_text LIKE '%<img%' LIMIT 8")
for qid, qt in cur.fetchall():
    print('=' * 60, qid)
    i = qt.find('<img')
    end = qt.find('>', i)
    print(qt[max(0,i-40):end+1])

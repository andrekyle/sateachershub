import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
for st in ['Q1.9','Q2.8','Q3.6','Q4.5','Q4.6','Q5.7']:
    r = c.execute("SELECT id, marks, question_text FROM question_bank_items WHERE subtopic = ?", (f'CAT P1 Nov 2025 - {st}',)).fetchone()
    print(st, '|', r[0], 'marks=', r[1])
    print('  TEXT:', repr(r[2]))
    print()

import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
for st in ['Q1.4','Q1.5','Q1.7','Q2.4','Q2.6','Q2.7']:
    rows = c.execute("SELECT subtopic, question_text, image_path FROM question_bank_items WHERE subtopic = ?",
                     (f'CAT P1 Nov 2025 - {st}',)).fetchall()
    for r in rows:
        print(r[0])
        print('  text:', repr(r[1])[:400])
        print('  image_path:', r[2])


import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("SELECT id, question_text, image_path FROM question_bank_items WHERE id='38987763-0e3f-4f5e-ad1f-623448851b85'").fetchone()
print('id:', r[0])
print('image_path:', r[2])
print('question_text:')
print(r[1])

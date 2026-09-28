import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("SELECT title, subject, paper_number, exam_date, cover_authority, cover_subtitle FROM generated_papers WHERE id='48c8c8d1-b356-490a-90a6-56868b67d10d'").fetchone()
print('title:', repr(r[0]))
print('subject:', repr(r[1]))
print('paper_number:', repr(r[2]))
print('exam_date:', repr(r[3]))
print('cover_authority:', repr(r[4]))
print('cover_subtitle:', repr(r[5]))

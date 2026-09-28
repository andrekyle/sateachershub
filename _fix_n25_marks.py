"""Sweep all CAT P1 Nov 2025 questions and remove embedded "(N)" / "(N )"
mark markers when a separate q.marks column will already render them."""
import sqlite3, re

c = sqlite3.connect('instance/brandcartel.db')
c.row_factory = sqlite3.Row

rows = c.execute(
    "SELECT id, subtopic, marks, question_text FROM question_bank_items "
    "WHERE subtopic LIKE 'CAT P1 Nov 2025 - %' ORDER BY subtopic"
).fetchall()

for r in rows:
    text = r['question_text'] or ''
    orig = text
    m = r['marks'] or 0
    # Standalone "(N)" on its own line.
    text = re.sub(r'(?m)^\s*\(\s*\d{1,3}\s*\)\s*$', '', text)
    # Trailing "(N)" or "(N )" at end of line where N matches q.marks.
    if m > 0:
        text = re.sub(rf'\s*\(\s*{m}\s*\)\s*(?=\n|$)', '', text)
    # Inline "(N) " before a "Save and close"/"Work in" trailer.
    text = re.sub(r'\s*\(\s*\d{1,3}\s*\)\s+(?=Save and close|Work in)', '\n\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if text != orig:
        c.execute("UPDATE question_bank_items SET question_text = ? WHERE id = ?", (text, r['id']))
        print(f"{r['subtopic']}: cleaned ({m} marks)")

c.commit()
print('done')

"""Remove the duplicated NOTE block that's currently embedded in Q6.1's
question_text. It originally appeared after the example figure in the
PDF, but in our render it appears above the figure (because q.image_path
displays after q.body), causing the appearance of duplication. Strip it
from the body — the figure and the rest of the stem are sufficient."""
import sqlite3, re
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute(
    "SELECT id, question_text FROM question_bank_items WHERE subtopic = ?",
    ('CAT P1 Nov 2025 - Q6.1',),
).fetchone()
print('BEFORE:')
print(r[1])
text = r[1] or ''
# Drop everything from "NOTE:" to the end of the stem (the second NOTE block).
text = re.split(r'\n\s*NOTE:\s*\n', text, maxsplit=1)[0]
text = re.sub(r'\s+$', '', text)
print('---AFTER:')
print(text)
c.execute("UPDATE question_bank_items SET question_text = ? WHERE id = ?",
          (text, r[0]))
c.commit()
print('done')

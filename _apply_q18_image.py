"""Set image_path on Q1.8 of CAT P2 Nov 2025 (paragraph-spacing icon)
and normalise question_type to 'short_answer' (matches other 1.x MC items).
"""
import sqlite3

QID = '8fe0ceee-4092-4c16-9126-506a62da55e1'  # paper id
PATH = 'uploads/cat_p2_n25/q1_8.png'

c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()

# look up Q1.8 (index 7 of section 0 of paper)
import json
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (QID,))
secs = json.loads(cur.fetchone()[0])
q18_id = secs[0]['question_ids'][7]
print('Q1.8 id:', q18_id)

cur.execute("""UPDATE question_bank_items
SET image_path = ?, question_type = 'short_answer'
WHERE id = ?""", (PATH, q18_id))
print('rows updated:', cur.rowcount)
c.commit()

cur.execute("SELECT id, question_type, marks, image_path, image_width, image_offset FROM question_bank_items WHERE id=?", (q18_id,))
print(cur.fetchone())

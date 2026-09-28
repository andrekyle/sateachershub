"""Fix Q4.11 marks (Section B, item 15) — group total leaked in."""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])

# Section B (index 1), item 15 = Q4.11 "Explain the process used by a 3D printer..."
qid = secs[1]['question_ids'][15]
cur.execute("SELECT marks, substr(question_text,1,60) FROM question_bank_items WHERE id=?", (qid,))
old, qt = cur.fetchone()
print(f'Section B item 15 ({qid}): old marks={old}, qt={qt!r}')
cur.execute("UPDATE question_bank_items SET marks=2 WHERE id=?", (qid,))
c.commit()
print('  -> set to 2')

# Re-verify Q4 total
qids = secs[1]['question_ids']
total = 0
for j in range(0, 16):
    cur.execute("SELECT marks FROM question_bank_items WHERE id=?", (qids[j],))
    total += cur.fetchone()[0] or 0
print(f'Q4 (items 0-15) total = {total}  (expected 25)')

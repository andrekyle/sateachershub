"""Fix bleed-through group totals on Section A items of CAT P2 Nov 2025.
- Q1.10 (item 9): marks 10 -> 1
- Q2.10 (item 19): marks 6 -> 1
After fix: Q1=10, Q2=10, Q3=5, TOTAL SECTION A = 25.
"""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
qids = secs[0]['question_ids']
fixes = [
    (9,  1, 'Q1.10'),
    (19, 1, 'Q2.10'),
]
for idx, new_marks, label in fixes:
    qid = qids[idx]
    cur.execute("SELECT marks FROM question_bank_items WHERE id=?", (qid,))
    old = cur.fetchone()[0]
    if old != new_marks:
        cur.execute("UPDATE question_bank_items SET marks=? WHERE id=?", (new_marks, qid))
        print(f'{label} (item {idx} {qid}): marks {old} -> {new_marks}')
    else:
        print(f'{label} already correct ({old})')
c.commit()

# verify
totals = []
for gi, start in enumerate(secs[0]['splits']):
    end = secs[0]['splits'][gi+1] if gi+1 < len(secs[0]['splits']) else len(qids)
    t = 0
    for j in range(start, end):
        cur.execute("SELECT marks FROM question_bank_items WHERE id=?", (qids[j],))
        t += cur.fetchone()[0] or 0
    print(f'Q{gi+1}: items {start}-{end-1} -> {t}')
    totals.append(t)
print(f'Section A total = {sum(totals)}')

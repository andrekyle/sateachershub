"""Inspect/fix Section B subitems for CAT P2 N25 paper.

PDF Q4 layout:
  4.1 (stem) 4.1.1 4.1.2 4.1.3 4.2 4.3 4.4 4.5 (stem) 4.5.1 4.5.2 4.6 4.7 4.8 4.9 4.10 4.11
=> indices 1,2,3 (children of 4.1) and 8,9 (children of 4.5) belong in `subitems`.
The stems at offset 0 and 7 are NOT in subitems (they're top-level).
"""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
sb = secs[1]
print('Section B existing subitems:', sb.get('subitems'))
print('Section B splits:', sb.get('splits'))
print('Section B qtitles:', sb.get('qtitles'))
print('Section B qinstructions[:1]:', (sb.get('qinstructions') or [''])[:2])
qids = sb['question_ids']
print()
print('Items 0-15 (Q4):')
for j in range(16):
    cur.execute("SELECT marks, question_type, substr(question_text,1,70) FROM question_bank_items WHERE id=?", (qids[j],))
    r = cur.fetchone()
    print(f'  [{j}] m={r[0]} type={r[1]} qt={r[2]!r}')

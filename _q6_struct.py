"""Inspect Q6.1 section structure to figure out where to inject NOTE."""
import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("SELECT sections FROM generated_papers WHERE id=?",
              ('48c8c8d1-b356-490a-90a6-56868b67d10d',)).fetchone()
s = json.loads(r[0])
sec0 = s[0]
print('keys at section level:', list(sec0.keys()))
# locate Q6.1 question id
qids = sec0.get('question_ids') or []
splits = sec0.get('splits') or []
subs = sec0.get('subitems') or []
print('splits:', splits)
print('subitems:', subs)
print('total qids:', len(qids))
# Q6 is group index 5 (0-based) -> qids[40:48]
print('Q6 qids:', qids[40:48])
# Find text in DB
for q in qids[40:48]:
    row = c.execute("SELECT subtopic FROM question_bank_items WHERE id=?", (q,)).fetchone()
    print(q, row[0] if row else None)

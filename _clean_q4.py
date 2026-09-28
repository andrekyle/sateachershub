"""Clean Q4 items in CAT P2 N25:
- Strip trailing ' (2)' / ' (N)' marks suffix from item 15 question_text
- Item 6 (Q4.4) has the path inline with whitespace; preserve via <pre>-style
  using triple backticks or a recognised marker the renderer keeps as-is.
  For now, just keep the text as-is — front-end whitespace handling is done
  in template.
"""
import sqlite3, json, re
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
qids = secs[1]['question_ids']

# 1) Strip trailing (N) marks suffix on item 15
qid15 = qids[15]
cur.execute("SELECT question_text FROM question_bank_items WHERE id=?", (qid15,))
old = cur.fetchone()[0]
new = re.sub(r'\s*\(\d+\)\s*$', '', old).rstrip()
if new != old:
    cur.execute("UPDATE question_bank_items SET question_text=? WHERE id=?", (new, qid15))
    print(f'item 15: stripped trailing marks; old end={old[-20:]!r} -> new end={new[-20:]!r}')

c.commit()
print('done')

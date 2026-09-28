"""Append (1) to the post_text of Q1.8 so the marks render at the right of
the last option (matches the DBE PDF) instead of next to the prompt.
"""
import sqlite3, json

PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()

cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
q18_id = secs[0]['question_ids'][7]
qp = secs[0].get('qpost_texts', {})
options = qp.get(q18_id, '')
if not options.endswith('(1)') and '(1)' not in options:
    options = options.rstrip() + ' (1)'
    qp[q18_id] = options
    secs[0]['qpost_texts'] = qp
    cur.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(secs), PID))
    c.commit()
    print('updated:', repr(options))
else:
    print('already has (1):', repr(options))

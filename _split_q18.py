"""Split Q1.8 of CAT P2 Nov 2025: keep prompt as question_text,
move options A-D into paper.sections[0]['qpost_texts'][qid] so they
render below the icon (matching the DBE PDF layout).
"""
import sqlite3, json

PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()

cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])

q18_id = secs[0]['question_ids'][7]
print('Q1.8 id:', q18_id)

cur.execute("SELECT question_text FROM question_bank_items WHERE id=?", (q18_id,))
qt = cur.fetchone()[0]
print('--- BEFORE ---')
print(repr(qt))

# Split into prompt and options. Options start at the first line beginning with
# whitespace + "A " (followed by 'To').
import re
m = re.search(r'\n\s*A\s+To adjust', qt)
if not m:
    raise SystemExit('could not find option-A boundary')

prompt = qt[:m.start()].rstrip()
options = qt[m.start():].lstrip('\n')

print('--- prompt ---')
print(repr(prompt))
print('--- options ---')
print(repr(options))

# Update question_text to prompt-only
cur.execute("UPDATE question_bank_items SET question_text=? WHERE id=?", (prompt, q18_id))

# Update paper.sections[0]['qpost_texts'] to include options block
sec0 = secs[0]
qpost = sec0.get('qpost_texts') or {}
if not isinstance(qpost, dict):
    qpost = {}
qpost[q18_id] = options
sec0['qpost_texts'] = qpost

cur.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(secs), PID))
c.commit()

print('--- AFTER ---')
cur.execute("SELECT question_text FROM question_bank_items WHERE id=?", (q18_id,))
print('question_text:', repr(cur.fetchone()[0]))
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs2 = json.loads(cur.fetchone()[0])
print('post_text:', repr(secs2[0]['qpost_texts'].get(q18_id, '')))

"""Strip the paper-wide preamble blurb from Section C instructions/qinstructions if present."""
import sqlite3, json, re

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
(raw,) = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(raw)
secC = secs[2]

BLURB_KEYS = [
    "will not be marked",
    "annexure a",
    "annexure b",
    "input mask character sheet",
    "web design software",
    "based on the scenario given below",
    "text editor",
]

def is_blurb(s):
    if not s:
        return False
    low = s.lower()
    return sum(1 for k in BLURB_KEYS if k in low) >= 2

changed = []

# Top-level section instructions
if is_blurb(secC.get('instructions') or ''):
    changed.append(('instructions', secC.get('instructions')[:60]))
    secC['instructions'] = ''

# qinstructions list
qi = secC.get('qinstructions') or []
for i, val in enumerate(qi):
    if is_blurb(val):
        changed.append((f'qinstructions[{i}]', val[:60]))
        qi[i] = ''
secC['qinstructions'] = qi

# qtitles - paranoia
qt = secC.get('qtitles') or []
for i, val in enumerate(qt):
    if is_blurb(val):
        changed.append((f'qtitles[{i}]', val[:60]))
        qt[i] = ''
secC['qtitles'] = qt

# question_bank_items texts within Section C
for qid in secC['question_ids']:
    row = c.execute("select question_text from question_bank_items where id=?", (qid,)).fetchone()
    if row and is_blurb(row[0]):
        changed.append((f'qid {qid}', row[0][:60]))
        c.execute("update question_bank_items set question_text=? where id=?", ('', qid))

if changed:
    c.execute("update generated_papers set sections=? where id=?", (json.dumps(secs), PAPER_ID))
    c.commit()
    print("Cleared blurb from:")
    for k, v in changed:
        print(f"  {k}: {v!r}")
else:
    print("No matching blurb found.")

"""Fix Q3.1-3.5 of CAT P2 Nov 2025:
- Underline the candidate word(s) using __word__ markup.
- Strip trailing extraction artefacts ((1), [5], TOTAL SECTION A) from 3.5.
"""
import sqlite3, json, re

PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
qids = secs[0]['question_ids']

UNDERLINES = {
    20: 'snipping tool',          # 3.1
    21: 'Digital divide',         # 3.2
    22: 'MAX',                    # 3.3
    23: 'Intellectual property',  # 3.4
    24: 'hyphen',                 # 3.5
}

for idx, word in UNDERLINES.items():
    qid = qids[idx]
    cur.execute("SELECT question_text FROM question_bank_items WHERE id=?", (qid,))
    qt = cur.fetchone()[0]

    # Strip trailing extraction junk (only relevant for 3.5)
    new = re.sub(r'\s*\(\d{1,3}\)\s*\n\s*\[\d{1,3}\]\s*\n.*?TOTAL SECTION.*$', '', qt, flags=re.DOTALL)
    new = re.sub(r'\s*\[\d{1,3}\]\s*$', '', new)
    new = re.sub(r'\s*\(\d{1,3}\)\s*$', '', new)
    new = new.rstrip()

    # Underline the candidate word (first occurrence). Don't double-wrap.
    if f'__{word}__' not in new:
        new2, n = re.subn(r'\b' + re.escape(word) + r'\b', f'__{word}__', new, count=1)
        if n == 0:
            print(f'  [WARN] could not find {word!r} in item {idx}')
        else:
            new = new2

    if new != qt:
        cur.execute("UPDATE question_bank_items SET question_text=? WHERE id=?", (new, qid))
        print(f'item {idx} (3.{idx-19}) updated:')
        print('  before:', repr(qt))
        print('  after :', repr(new))
    else:
        print(f'item {idx} (3.{idx-19}) unchanged')

c.commit()
print('\n--- VERIFY ---')
for idx in UNDERLINES:
    cur.execute("SELECT question_text FROM question_bank_items WHERE id=?", (qids[idx],))
    print(f'3.{idx-19}:', repr(cur.fetchone()[0]))

import sqlite3, json
con = sqlite3.connect('instance/brandcartel.db')
cur = con.cursor()
pid = 'd1c9a55b-0fb2-4309-aae0-7a994e57ed4c'
row = cur.execute("SELECT instructions, sections, sections_original, sections_moderated, sections_final FROM generated_papers WHERE id=?", (pid,)).fetchone()
labels = ['instructions','sections','sections_original','sections_moderated','sections_final']
for lab, val in zip(labels, row):
    print('====', lab, 'len=', len(val or ''))
    if lab == 'instructions':
        print(repr(val))
        continue
    if not val: continue
    try:
        secs = json.loads(val)
    except Exception as e:
        print('JSON err', e); continue
    for si, s in enumerate(secs):
        print(f'-- sec {si} title={s.get("title")!r}')
        print('   instructions=', repr(s.get('instructions')))
        print('   qinstructions=', repr(s.get('qinstructions')))
        print('   question_ids=', s.get('question_ids'))
        print('   splits=', s.get('splits'))
# Also search all 6 question rows for NOTE text
qbcols = [r[1] for r in cur.execute("PRAGMA table_info(question_bank_items)").fetchall()]
print('QBCOLS:', qbcols)
secs = json.loads(row[4] or row[1])
all_qids = []
for s in secs:
    all_qids.extend(s.get('question_ids') or [])
for qid in all_qids:
    q = cur.execute("SELECT id, question_type, question_text, answer_text FROM question_bank_items WHERE id=?", (qid,)).fetchone()
    if q:
        print('QID', q[0], 'type=', q[1])
        print('  QTEXT:', repr(q[2]))

import sqlite3, json
con = sqlite3.connect('instance/brandcartel.db')
con.row_factory = sqlite3.Row
cur = con.cursor()
pid = 'd1c9a55b-0fb2-4309-aae0-7a994e57ed4c'
row = cur.execute("SELECT sections, sections_final FROM generated_papers WHERE id=?", (pid,)).fetchone()
secs_json = row['sections_final'] or row['sections']
secs = json.loads(secs_json)
qids = []
for si, s in enumerate(secs):
    for qi, qid in enumerate(s.get('question_ids') or []):
        qids.append((si, qi, qid))
print('TOTAL QIDS:', len(qids))
# describe questions table
cols = [r[1] for r in cur.execute("PRAGMA table_info(question_bank_items)").fetchall()]
print('QCOLS:', cols)
text_cols = [c for c in cols if 'text' in c.lower() or c in ('display_text','question_text','answer_text')]
hits = []
for si, qi, qid in qids:
    q = cur.execute(f"SELECT * FROM question_bank_items WHERE id=?", (qid,)).fetchone()
    if not q: continue
    for c in text_cols:
        v = q[c] or ''
        if 'Do NOT simply use' in v or 'NO marks will be awarded if only FALSE' in v or 'NO mark will be awarded if only FALSE' in v:
            hits.append((si, qi, qid, c, v))
print('HITS:', len(hits))
for h in hits:
    print('---')
    print('SI=', h[0], 'QI=', h[1], 'QID=', h[2], 'COL=', h[3])
    print(repr(h[4]))

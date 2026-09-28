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
for si, qi, qid in qids:
    q = cur.execute(f"SELECT * FROM question_bank_items WHERE id=?", (qid,)).fetchone()
    if not q:
        print(f"QID {qid} NOT FOUND")
        continue
    print(f"--- QID {qid} ---")
    print("TEXT:", q['question_text'])
    print("ANSWER:", q['answer_text'])

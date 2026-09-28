import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(r[0])
secB = secs[1]
qids = secB['question_ids']
splits = secB['splits']
print("splits:", splits, "total qids:", len(qids))

print("\n=== Q5 items (idx 16..23) ===")
total = 0
for i in range(splits[1], splits[2]):
    qid = qids[i]
    row = c.execute("select id, question_text, marks from question_bank_items where id=?", (qid,)).fetchone()
    if not row:
        print(f"[{i}] qid={qid} NOT FOUND"); continue
    qt = (row[1] or '').replace('\n', ' ')[:80]
    marks = row[2]
    total += marks or 0
    print(f"[{i}] marks={marks} | {qt}")
print(f"Q5 sum of marks={total}")

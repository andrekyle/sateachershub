import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(r[0])
secB = secs[1]
qids = secB['question_ids']
splits = secB['splits']  # [0, 16, 24, 29, 34]
print("splits:", splits, "n:", len(qids))
print("Q6 range: splits[2..3] =", splits[2], "..", splits[3])
print("\n=== Q6 items (idx 24..28) ===")
total = 0
for i in range(splits[2], splits[3]):
    qid = qids[i]
    row = c.execute("select id, question_text, marks, image_path, image_width from question_bank_items where id=?", (qid,)).fetchone()
    if not row: print(f"[{i}] qid={qid} NOT FOUND"); continue
    qt = (row[1] or '').replace('\n', ' ')
    marks = row[2]
    total += marks or 0
    print(f"[{i}] marks={marks} img={row[3]} w={row[4]}")
    print(f"    text: {qt}")
print(f"Q6 sum of marks={total}")
print("\nqinstructions[2] (Q6 group intro):", repr(secB.get('qinstructions', [''])[2] if len(secB.get('qinstructions',[]))>2 else None))
print("qtitles[2]:", repr(secB.get('qtitles', [''])[2] if len(secB.get('qtitles',[]))>2 else None))
print("\nsubitems for Q6:")
subi = secB.get('subitems', [])
for i in range(splits[2], splits[3]):
    if i < len(subi):
        print(f"  [{i}]: {repr(subi[i])[:200]}")

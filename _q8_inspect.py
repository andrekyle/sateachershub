import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(r[0])
secB = secs[1]
qids = secB['question_ids']
splits = secB['splits']
print("splits:", splits, "n:", len(qids))
# Q8 is the last group: indices splits[4]..end (34..49)
start = splits[4]
end = len(qids)
print(f"Q8 range: {start}..{end-1}")
total = 0
for i in range(start, end):
    qid = qids[i]
    row = c.execute("select id, question_text, marks, image_path, image_width from question_bank_items where id=?", (qid,)).fetchone()
    if not row: print(f"[{i}] NOT FOUND"); continue
    qt = (row[1] or '').replace('\n', ' / ')[:120]
    total += row[2] or 0
    print(f"[{i}] m={row[2]} img={row[3]} w={row[4]}")
    print(f"    {qt}")
print(f"Q8 total marks={total}")
print("\nsubitems:", secB.get('subitems', []))
print("qtitles:", secB.get('qtitles', []))
print("qinstructions[4]:", repr(secB.get('qinstructions',['',]*5)[4]))
print("qpost_texts keys for Q8:")
for k,v in (secB.get('qpost_texts') or {}).items():
    if k in qids[start:end]:
        print(f"  {k}: {v!r}")

import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(r[0])
print("num sections:", len(secs))
for si, s in enumerate(secs):
    print(f"\n--- Section [{si}] keys: {list(s.keys())}")
    print(f"  title={s.get('title')!r}")
    print(f"  question_ids count={len(s.get('question_ids', []))}")
    print(f"  splits={s.get('splits')}")
    print(f"  marks={s.get('marks')}")
    print(f"  qtitles={s.get('qtitles')}")
    print(f"  qinstructions={s.get('qinstructions')}")

# Section C details
if len(secs) >= 3:
    secC = secs[2]
    qids = secC['question_ids']
    print(f"\n=== Section C items ({len(qids)}) ===")
    for i, qid in enumerate(qids):
        row = c.execute("select question_text, marks, image_path, image_width from question_bank_items where id=?", (qid,)).fetchone()
        if not row:
            print(f"[{i}] qid={qid} NOT FOUND"); continue
        qt = (row[0] or '').replace('\n', ' / ')[:100]
        print(f"[{i}] m={row[1]} img={row[2] or '-'} w={row[3]} | {qt}")
    print(f"subitems: {secC.get('subitems', [])}")
    print(f"qpost_texts: {list((secC.get('qpost_texts') or {}).keys())}")

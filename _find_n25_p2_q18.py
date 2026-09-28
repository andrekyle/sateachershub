import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()

PAPERS = [
    ('48c8c8d1-b356-490a-90a6-56868b67d10d', 'CAT P1 Nov 2025'),
    ('8fe0ceee-4092-4c16-9126-506a62da55e1', 'CAT P2 Nov 2025'),
]

for pid, name in PAPERS:
    print('=' * 70)
    print(name, pid)
    cur.execute("SELECT sections FROM generated_papers WHERE id=?", (pid,))
    secs = json.loads(cur.fetchone()[0])
    for si, s in enumerate(secs):
        qids = s.get('question_ids') or []
        title = s.get('section_label') or s.get('title') or ''
        if si <= 1 or 'QUESTION 1' in title.upper() or 'MULTIPLE' in title.upper():
            print(f'  section {si}: {title!r} ({len(qids)} qs)')
            for j, qid in enumerate(qids[:12]):
                cur.execute("SELECT id, question_type, marks, substr(question_text,1,140), substr(answer_text,1,80) FROM question_bank_items WHERE id=?", (qid,))
                row = cur.fetchone()
                if row:
                    print(f'    [{j}] {row[1]:18s} m={row[2]:>3} {row[3]!r}  ans={row[4]!r}')
                    if j == 7:
                        cur.execute("SELECT question_text, answer_text, question_type, marks FROM question_bank_items WHERE id=?", (qid,))
                        qt, at, qty, mk = cur.fetchone()
                        print('       *** FULL Q1.8 ***')
                        print('       qt:', repr(qt))
                        print('       at:', repr(at))
                        print('       type:', qty, 'marks:', mk)

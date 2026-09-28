import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT id, sections FROM generated_papers WHERE title='CAT P2 Nov 2023'")
row = cur.fetchone()
if not row:
    print('Paper not found; listing titles:')
    for (t,) in cur.execute("SELECT title FROM generated_papers"):
        print(' -', t)
    raise SystemExit
pid, secs_json = row
sections = json.loads(secs_json)
print('PID=', pid)
for i, s in enumerate(sections):
    print(f"\n=== Sec {i}: {s.get('title')!r} ===")
    print('  splits=', s.get('splits'))
    print('  qtitles=', s.get('qtitles'))
    print('  qinstructions=', json.dumps(s.get('qinstructions'), ensure_ascii=False))
    print('  instructions=', repr(s.get('instructions')))
    print('  #qids=', len(s.get('question_ids', [])))

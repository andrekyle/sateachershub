import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
for si, s in enumerate(secs):
    print(f'section {si}: marks={s.get("marks")} section_label={s.get("section_label")!r} title={s.get("title")!r} qcount={len(s.get("question_ids") or [])} splits={s.get("splits") or s.get("group_splits")}')
    print('   keys:', list(s.keys()))
    print('   suppress_total:', s.get('suppress_total'))

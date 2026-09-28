"""Dump sec.instructions and sec.qinstructions for all 3 sections."""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
for i, s in enumerate(secs):
    print(f'\n=== Section {i} ({s.get("title")}) ===')
    print(' instructions =', repr(s.get('instructions', ''))[:600])
    print(' qinstructions =', s.get('qinstructions') or [])

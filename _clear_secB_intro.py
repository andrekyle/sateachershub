"""Clear Section B sec.instructions — PDF goes straight from
   'QUESTION 4: SYSTEMS TECHNOLOGIES' into '4.1 Learners at a school...'.
"""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
secs[1]['instructions'] = ''
qi = list(secs[1].get('qinstructions') or [])
while len(qi) < 5:
    qi.append('')
qi[0] = ''
secs[1]['qinstructions'] = qi
cur.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(secs), PID))
c.commit()
print('Cleared Section B intro.')

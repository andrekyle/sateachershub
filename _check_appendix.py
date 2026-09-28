import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
row = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(row[0])
# search the whole JSON blob for 'HTML TAG' or 'INPUT MASK'
blob = json.dumps(secs)
for needle in ('HTML TAG', 'INPUT MASK', 'tag sheet', 'input mask'):
    idx = blob.lower().find(needle.lower())
    if idx != -1:
        print(needle, '@', idx, '->', blob[max(0,idx-60):idx+120])
    else:
        print(needle, 'NOT FOUND in sections JSON')

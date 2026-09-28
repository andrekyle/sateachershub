import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
c.row_factory = sqlite3.Row
r = c.execute("SELECT * FROM generated_papers WHERE id='48c8c8d1-b356-490a-90a6-56868b67d10d'").fetchone()
print('COLS:', list(r.keys()))
for k in r.keys():
    v = r[k]
    s = str(v) if v is not None else ''
    print(f'\n=== {k} ===')
    print(s[:1500])

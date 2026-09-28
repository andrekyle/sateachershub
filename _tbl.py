import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
tables = [r[0] for r in c.execute("select name from sqlite_master where type='table'").fetchall()]
print('\n'.join(t for t in tables if 'question' in t.lower() or 'bank' in t.lower()))

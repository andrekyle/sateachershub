import sqlite3
con = sqlite3.connect('instance/brandcartel.db')
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

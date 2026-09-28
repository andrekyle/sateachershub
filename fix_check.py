import sqlite3
import os

db_path = 'instance/brandcartel.db'
paper_id = '5a2d7117-fe07-4045-8588-b5a169cf3713'

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT instructions FROM generated_papers WHERE id=?', (paper_id,))
row = cur.fetchone()

if row:
    val = row[0]
    print(f"Full value: {repr(val)}")
    print(f"\\r\\n\\r\\n count: {val.count('\r\n\r\n')}")
    print(f"\\n\\n count: {val.count('\n\n')}")
    print(f"\\r\\n•  count: {val.count('\r\n• ')}")
    print(f"\\n•  count: {val.count('\n• ')}")
else:
    print("ID not found")

conn.close()

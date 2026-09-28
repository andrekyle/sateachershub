"""Inspect Q4 items - check image_path / suffixes / etc."""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
qids = secs[1]['question_ids']

print('--- Item 6 (4.4 - path with A, B) ---')
cur.execute("SELECT id, marks, question_type, image_path, image_width, question_text FROM question_bank_items WHERE id=?", (qids[6],))
r = cur.fetchone()
print(f'id={r[0]}')
print(f'marks={r[1]}, type={r[2]}, img={r[3]!r}, w={r[4]}')
print(f'qt={r[5]!r}')

print()
print('--- Item 15 (4.11 - 3D printer) ---')
cur.execute("SELECT id, marks, question_type, image_path, question_text FROM question_bank_items WHERE id=?", (qids[15],))
r = cur.fetchone()
print(f'id={r[0]}')
print(f'marks={r[1]}, type={r[2]}, img={r[3]!r}')
print(f'qt={r[4]!r}')

print()
print('--- Item 0 (4.1 stem) ---')
cur.execute("SELECT id, marks, question_type, image_path, question_text FROM question_bank_items WHERE id=?", (qids[0],))
r = cur.fetchone()
print(f'id={r[0]}')
print(f'marks={r[1]}, type={r[2]}, img={r[3]!r}')
print(f'qt={r[4]!r}')

print()
print('--- Item 7 (4.5 stem) ---')
cur.execute("SELECT id, marks, question_type, image_path, question_text FROM question_bank_items WHERE id=?", (qids[7],))
r = cur.fetchone()
print(f'id={r[0]}')
print(f'marks={r[1]}, type={r[2]}, img={r[3]!r}')
print(f'qt={r[4]!r}')

import sqlite3
import re
import os
import sys

db_path = 'instance/brandcartel.db'
columns = [
    'instructions', 'sections', 'sections_original', 'sections_moderated', 
    'sections_final', 'cover_extra_note', 'sub_header', 'cover_authority', 
    'cover_subtitle', 'header_left', 'header_right', 'footer_left', 
    'footer_center', 'footer_right', 'memo_title', 'header_original', 
    'moderator_overrides', 'data_files'
]

bullets = ['\uf0b7', '\uf0a7', '\uf076', '\uf0a8']
real_bullet = '\u2022'

def process_text(text):
    if not text:
        return text
    original = text
    for b in bullets:
        text = text.replace(b, '\n' + real_bullet)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text if text != original else None

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"SELECT id, {', '.join(columns)} FROM generated_papers")
    rows = cur.fetchall()
    scanned = 0
    updated = 0
    column_counts = {col: 0 for col in columns}
    for row in rows:
        scanned += 1
        row_id = row[0]
        updates = {}
        for i, col in enumerate(columns):
            val = row[i+1]
            if isinstance(val, str):
                new_val = process_text(val)
                if new_val is not None:
                    updates[col] = new_val
                    column_counts[col] += 1
        if updates:
            set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
            params = list(updates.values()) + [row_id]
            cur.execute(f"UPDATE generated_papers SET {set_clause} WHERE id = ?", params)
            updated += 1
    conn.commit()
    conn.close()
    print(f"Rows scanned: {scanned}")
    print(f"Rows updated: {updated}")
    print("Per-column modifications:")
    for col in columns:
        if column_counts[col] > 0:
            print(f"  {col}: {column_counts[col]}")
except Exception as e:
    print(f"Error: {e}")

import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
c.execute("UPDATE question_bank_items SET image_path = REPLACE(image_path, '/static/', '') "
          "WHERE subtopic LIKE 'CAT P1 Nov 2025 - %' AND image_path LIKE '/static/%'")
c.commit()
for r in c.execute("SELECT subtopic, image_path FROM question_bank_items "
                   "WHERE subtopic LIKE 'CAT P1 Nov 2025 - %' AND image_path != ''").fetchall():
    print(r)

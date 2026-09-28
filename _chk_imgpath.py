import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
# How is the working q4_4 image_path stored?
rows = c.execute("select id, image_path from question_bank_items where image_path like '%q4_4%' or image_path like '%cat_p2_n25%' limit 10").fetchall()
for r in rows: print(r)

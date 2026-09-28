import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
qid = 'a2d25dd5-db4b-4638-963c-b201e63a1042'
c.execute("update question_bank_items set image_path=? where id=?", ('uploads/cat_p2_n25/q6_5.png', qid))
c.commit()
print(c.execute("select image_path from question_bank_items where id=?", (qid,)).fetchone())

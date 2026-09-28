import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
for qid in ['36989481-6cf5-4ecf-b765-e4acd566984e','773d462c-a76f-4593-a6c3-05b02af2f761','061eb638-7f6c-4c74-b522-d2b018251e83']:
    r = c.execute("SELECT id,subtopic,question_text,marks FROM question_bank_items WHERE id=?", (qid,)).fetchone()
    print('===', r[1], '(marks',r[3],')===')
    print(r[2])
    print()

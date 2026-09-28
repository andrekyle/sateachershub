import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
with app.app_context():
    q = QuestionBankItem.query.filter(QuestionBankItem.id.like('4a812e41%')).first()
    q.question_text = ("Draw a diagram to show what will be displayed in a web browser when this "
                       "HTML code is run:\n\n[[Q89CODE]]")
    db.session.commit()
    print('8.9 code box wired; marks=', q.marks)

    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    qids = secs[1]['question_ids']
    q8 = sum((db.session.get(QuestionBankItem, qids[i]).marks or 0) for i in range(40, 53))
    secB = sum((db.session.get(QuestionBankItem, x).marks or 0) for x in qids)
    print('Q8:', q8, 'Section B:', secB)
    owner = p.owner_id

c = app.test_client()
with c.session_transaction() as sess:
    sess['_user_id'] = owner; sess['user_id'] = owner; sess['user_role'] = 'teacher'
html = c.get(f'/teacher/generator/{PID}/preview').get_data(as_text=True)
import re
i = html.find('code-box')
# find the 8.9 code box (search for DESCRIPTION in a code-box)
j = html.find('DESCRIPTION', html.find('Draw a diagram'))
print('code-box + DESCRIPTION present:', 'code-box' in html and j > 0)
if j > 0:
    seg = html[j-400:j+300]
    txt = re.sub(r'<br\s*/?>', ' / ', seg)
    txt = re.sub(r'&lt;', '<', txt); txt = re.sub(r'&gt;', '>', txt); txt = re.sub(r'&nbsp;', '.', txt)
    txt = re.sub(r'<[^>]+>', '', txt)
    print(txt[:500])

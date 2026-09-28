import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
with app.app_context():
    # 7.1 italic "social engineering"
    q32 = QuestionBankItem.query.filter(QuestionBankItem.id.like('580bf8a9%')).first()
    q32.question_text = "Define the concept of <i>social engineering</i>."

    # 7.6 stem: strip leaked R1 500, wire advert
    q37 = QuestionBankItem.query.filter(QuestionBankItem.id.like('13818378%')).first()
    q37.question_text = "Study the advertisement below and answer the questions that follow."
    q37.image_path = 'uploads/cat_p2_mj21/q7_6_advert.png'
    q37.image_width = 42
    tags = q37.tags or ''
    if 'noborder' not in tags:
        q37.tags = tags + ',noborder'
    db.session.commit()
    print('7.1 italic + 7.6 advert wired; tags:', q37.tags)

    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    qids = secs[1]['question_ids']
    q7 = sum((db.session.get(QuestionBankItem, qids[i]).marks or 0) for i in range(32, 40))
    secB = sum((db.session.get(QuestionBankItem, x).marks or 0) for x in qids)
    print('Q7 total:', q7, 'Section B total:', secB)
    owner = p.owner_id

c = app.test_client()
with c.session_transaction() as sess:
    sess['_user_id'] = owner; sess['user_id'] = owner; sess['user_role'] = 'teacher'
html = c.get(f'/teacher/generator/{PID}/preview').get_data(as_text=True)
print('advert img present:', 'q7_6_advert.png' in html)
print('social engineering italic:', '<em>social engineering</em>' in html or '<i>social engineering</i>' in html)
i = html.find('q7_6_advert.png')
if i > 0:
    print('no-border near advert:', 'no-border' in html[i-300:i+80])

import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
with app.app_context():
    # 8.4 screenshot
    q43 = QuestionBankItem.query.filter(QuestionBankItem.id.like('c7e3f930%')).first()
    q43.question_text = ("What is the purpose of the small square in the bottom right-hand "
                         "corner of cell C1, indicated by the arrow in the screenshot below?")
    q43.image_path = 'uploads/cat_p2_mj21/q8_4_fillhandle.png'
    q43.image_width = 60
    if 'noborder' not in (q43.tags or ''):
        q43.tags = (q43.tags or '') + ',noborder'

    # 8.6 tables
    q45 = QuestionBankItem.query.filter(QuestionBankItem.id.like('5c7ce32b%')).first()
    q45.question_text = ("Explain how the data in the 'original data' table below was processed "
                         "to give the data shown in the 'processed data' table.")
    q45.image_path = 'uploads/cat_p2_mj21/q8_6_tables.png'
    q45.image_width = 82
    if 'noborder' not in (q45.tags or ''):
        q45.tags = (q45.tags or '') + ',noborder'
    db.session.commit()

    # put the mark below each figure via qpost (both papers)
    for pid in ['daa560a4-2a50-4a22-8425-cadafeeb4ee0',
                'da7ab572-7761-453a-b4a2-39df5bf2b3ad']:
        p = GeneratedPaper.query.get(pid)
        if not p:
            continue
        secs = json.loads(p.sections)
        qpt = secs[1].get('qpost_texts') or {}
        qpt[q43.id] = '(1)'
        qpt[q45.id] = '(2)'
        secs[1]['qpost_texts'] = qpt
        p.sections = json.dumps(secs, ensure_ascii=False)
        db.session.commit()
    print('wired 8.4 + 8.6')

    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    qids = secs[1]['question_ids']
    q8 = sum((db.session.get(QuestionBankItem, qids[i]).marks or 0) for i in range(40, 53))
    secB = sum((db.session.get(QuestionBankItem, x).marks or 0) for x in qids)
    print('Q8 total:', q8, 'Section B:', secB)
    owner = p.owner_id

c = app.test_client()
with c.session_transaction() as sess:
    sess['_user_id'] = owner; sess['user_id'] = owner; sess['user_role'] = 'teacher'
html = c.get(f'/teacher/generator/{PID}/preview').get_data(as_text=True)
print('8.4 img present:', 'q8_4_fillhandle.png' in html)
print('8.6 img present:', 'q8_6_tables.png' in html)
print('cell C1 bold:', '<strong>cell C1</strong>' in html or 'cell <strong>C1</strong>' in html)

import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
SCENARIO = ("The various Covid-19 protocols that were imposed by the government to restrict the "
            "spread of the virus impacted on school attendance.")

with app.app_context():
    # 10.1.1 italic
    q21 = QuestionBankItem.query.filter(QuestionBankItem.id.like('3241f70d%')).first()
    q21.question_text = "Define the concept of <i>mobile learning (m-learning)</i>."
    db.session.commit()
    print('10.1.1 italic set')

    for pid in ['daa560a4-2a50-4a22-8425-cadafeeb4ee0',
                'da7ab572-7761-453a-b4a2-39df5bf2b3ad']:
        p = GeneratedPaper.query.get(pid)
        if not p:
            continue
        secs = json.loads(p.sections)
        s2 = secs[2]
        qt = s2.get('qtitles') or ['', '']
        while len(qt) < 2: qt.append('')
        qt[1] = 'INTEGRATED SCENARIO'
        s2['qtitles'] = qt
        qi = s2.get('qinstructions') or ['', '']
        while len(qi) < 2: qi.append('')
        qi[1] = SCENARIO
        s2['qinstructions'] = qi
        p.sections = json.dumps(secs, ensure_ascii=False)
        db.session.commit()
        print(pid[:8], 'scenario set')

    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    qids = secs[2]['question_ids']
    q10 = sum((db.session.get(QuestionBankItem, qids[i]).marks or 0) for i in range(20, 40))
    secC = sum((db.session.get(QuestionBankItem, x).marks or 0) for x in qids)
    print('Q10:', q10, 'Section C:', secC)
    owner = p.owner_id

c = app.test_client()
with c.session_transaction() as sess:
    sess['_user_id'] = owner; sess['user_id'] = owner; sess['user_role'] = 'teacher'
html = c.get(f'/teacher/generator/{PID}/preview').get_data(as_text=True)
print('Q10 INTEGRATED SCENARIO title (2nd):', html.count('INTEGRATED SCENARIO'))
print('scenario text:', 'various Covid-19 protocols that were imposed' in html)
print('m-learning italic:', '<em>mobile learning (m-learning)</em>' in html or '<i>mobile learning (m-learning)</i>' in html)
import re
txt = re.sub(r'<[^>]+>', ' ', html); txt = re.sub(r'\s+', ' ', txt)
m = re.search(r'TOTAL SECTION C:\s*\[?\s*(\d+)', txt)
print('TOTAL SECTION C:', m.group(1) if m else '?')

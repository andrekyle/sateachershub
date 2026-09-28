import json
from app import app, db, GeneratedPaper

MCQ_INTRO = ("Various options are given as possible answers to the following questions. "
             "Choose the answer and write only the letter (A\u2013D) next to the question "
             "numbers (1.1 to 1.10) in the ANSWER BOOK, e.g. 1.11 D.")

with app.app_context():
    for pid in ['daa560a4-2a50-4a22-8425-cadafeeb4ee0',
                'da7ab572-7761-453a-b4a2-39df5bf2b3ad']:
        p = GeneratedPaper.query.get(pid)
        if not p:
            continue
        secs = json.loads(p.sections)
        qi = secs[0].get('qinstructions') or ['', '', '']
        while len(qi) < 3:
            qi.append('')
        qi[0] = MCQ_INTRO
        secs[0]['qinstructions'] = qi
        p.sections = json.dumps(secs, ensure_ascii=False)
        db.session.commit()
        print(pid[:8], 'Q1 MCQ intro set')

    PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
    p = GeneratedPaper.query.get(PID)
    owner = p.owner_id

c = app.test_client()
with c.session_transaction() as sess:
    sess['_user_id'] = owner; sess['user_id'] = owner; sess['user_role'] = 'teacher'
html = c.get(f'/teacher/generator/{PID}/preview').get_data(as_text=True)
print('MCQ intro present:', 'Various options are given as possible answers' in html)
print('e.g. 1.11 D present:', 'e.g. 1.11 D' in html)

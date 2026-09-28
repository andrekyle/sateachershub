import json
from app import app, db, GeneratedPaper, QuestionBankItem

SCENARIO = ("The Covid-19 pandemic necessitated health screening at the entrances to all public "
            "facilities, such as schools, libraries and clinics, to limit the spread of the coronavirus.")

with app.app_context():
    # 9.4 stem + spreadsheet
    q7 = QuestionBankItem.query.filter(QuestionBankItem.id.like('a13f265b%')).first()
    q7.question_text = "The screenshot of part of a spreadsheet below shows some health screening data of the learners:"
    q7.image_path = 'uploads/cat_p2_mj21/q9_4_screening.png'
    q7.image_width = 62
    if 'noborder' not in (q7.tags or ''):
        q7.tags = (q7.tags or '') + ',noborder'

    # 9.5 stem + design view
    q11 = QuestionBankItem.query.filter(QuestionBankItem.id.like('80002798%')).first()
    q11.question_text = ("Below is the Design View of a database table with learner information "
                         "and the field properties sheet of the **Date of birth** field.")
    q11.image_path = 'uploads/cat_p2_mj21/q9_5_design.png'
    q11.image_width = 92
    if 'noborder' not in (q11.tags or ''):
        q11.tags = (q11.tags or '') + ',noborder'

    # 9.5.1 bold Date of birth
    q12 = QuestionBankItem.query.filter(QuestionBankItem.id.like('4431cbbc%')).first()
    q12.question_text = ("Suggest THREE improvements that could be made to the **Date of birth** "
                         "field to ensure the entry of valid data.")
    db.session.commit()
    print('9.4/9.5 wired')

    # scenario title + intro on both papers
    for pid in ['daa560a4-2a50-4a22-8425-cadafeeb4ee0',
                'da7ab572-7761-453a-b4a2-39df5bf2b3ad']:
        p = GeneratedPaper.query.get(pid)
        if not p:
            continue
        secs = json.loads(p.sections)
        s2 = secs[2]
        qt = s2.get('qtitles') or ['', '']
        while len(qt) < 2: qt.append('')
        qt[0] = 'INTEGRATED SCENARIO'
        s2['qtitles'] = qt
        qi = s2.get('qinstructions') or ['', '']
        while len(qi) < 2: qi.append('')
        qi[0] = SCENARIO
        s2['qinstructions'] = qi
        p.sections = json.dumps(secs, ensure_ascii=False)
        db.session.commit()
        print(pid[:8], 'scenario set')

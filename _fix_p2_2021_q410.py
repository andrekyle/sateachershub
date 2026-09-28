import json
from app import app, db, GeneratedPaper, QuestionBankItem

QID = '8778ed57'
IMG = 'uploads/cat_p2_mj21/q4_10_sendto.png'
BODY = ("A user tries to save a word processing document on the Desktop by "
        "performing the action as shown in the screenshot below.")
POST = ("Give the reason why the user is NOT successful AND give a solution to "
        "this problem. (2)")

with app.app_context():
    q = QuestionBankItem.query.filter(QuestionBankItem.id.like(QID + '%')).first()
    full_qid = q.id
    q.question_text = BODY
    q.image_path = IMG
    q.image_width = 85
    q.marks = 2
    db.session.commit()
    print('wired image to', full_qid)

    for pid in ['daa560a4-2a50-4a22-8425-cadafeeb4ee0',
                'da7ab572-7761-453a-b4a2-39df5bf2b3ad']:
        p = GeneratedPaper.query.get(pid)
        if not p:
            print(pid, 'MISSING'); continue
        secs = json.loads(p.sections)
        s1 = secs[1]
        qpt = s1.get('qpost_texts') or {}
        qpt[full_qid] = POST
        s1['qpost_texts'] = qpt
        p.sections = json.dumps(secs, ensure_ascii=False)
        db.session.commit()
        print(pid[:8], 'qpost set')

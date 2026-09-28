from app import app, db, QuestionBankItem
QID = 'd6e0883e-d771-45c4-bf0a-7978948a26ec'
with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('BEFORE marks =', q.marks)
    print('question_text:', q.question_text[:200])
    q.marks = 2
    db.session.commit()
    q2 = db.session.get(QuestionBankItem, QID)
    print('AFTER  marks =', q2.marks)

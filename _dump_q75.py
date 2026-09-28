from app import app, db, QuestionBankItem
QID = 'd6e0883e-d771-45c4-bf0a-7978948a26ec'  # Q7.5 software piracy
with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('marks=', q.marks)
    print('Q:', repr(q.question_text))
    print('--- A ---')
    print(q.answer_text)

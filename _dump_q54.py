from app import app, db, QuestionBankItem
QID = '61c78f7a-baa7-45b9-a0f9-4536ab7b58dc'
with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('marks=', q.marks)
    print('Qtext:', repr(q.question_text))
    print('--- A ---')
    print(q.answer_text)
    print('--- repr ---')
    print(repr(q.answer_text))

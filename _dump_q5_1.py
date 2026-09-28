from app import app, db, QuestionBankItem
with app.app_context():
    q = db.session.get(QuestionBankItem, 'a7f6ebb2-7631-4d3f-b984-9acc1d74f1a6')
    print('marks=', q.marks)
    print('Q text:', repr(q.question_text))
    print('A text:', repr(q.answer_text))

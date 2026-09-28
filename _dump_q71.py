from app import app, db, QuestionBankItem
QID = '37aedd9a-77fe-44a5-a133-e62bbefdb429'
with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('marks=', q.marks)
    print('Q:', repr(q.question_text))
    print('A:')
    print(q.answer_text)
    print('repr A:', repr(q.answer_text))

from app import app, db, QuestionBankItem
QID = 'd89ab697-2f53-4156-800b-eb775a265c43'
with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('marks=', q.marks)
    print('Q:', repr(q.question_text))
    print('--- A ---')
    print(q.answer_text)
    print('--- repr ---')
    print(repr(q.answer_text))

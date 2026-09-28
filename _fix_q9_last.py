from app import app, db, QuestionBankItem
with app.app_context():
    q = db.session.get(QuestionBankItem, 'df34dd53-0634-41d3-a407-51cbf5738b9c')
    q.marks = 2
    # also clean trailing "(2)" mark token from the text since the template auto-renders the badge
    q.question_text = (
        "During the competition, plagiarism leads to immediate disqualification.\n\n"
        "Briefly explain the concept plagiarism."
    )
    db.session.commit()
    print('updated. marks=', q.marks)
    print(repr(q.question_text))

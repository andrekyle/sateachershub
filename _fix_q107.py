from app import app, db, QuestionBankItem
with app.app_context():
    q = db.session.get(QuestionBankItem, '27f88603-cba0-407a-a63c-64895c8b1a29')
    q.question_text = (
        "A video with all the highlights will be created and uploaded to the school's "
        "website. The link will be e-mailed to the parents, using a distribution list.\n\n"
        "State TWO advantages of using a distribution list."
    )
    q.marks = 2
    db.session.commit()
    print('updated. marks=', q.marks)
    print(repr(q.question_text))

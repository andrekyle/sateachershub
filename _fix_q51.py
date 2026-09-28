"""Normalize Q5.1 memo answer: keep heading on its own line, collapse the
body's internal hard line breaks to single spaces so it wraps naturally."""
from app import app, db, QuestionBankItem

QID = 'a7f6ebb2-7631-4d3f-b984-9acc1d74f1a6'

with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('BEFORE marks=', q.marks)
    print('BEFORE A:', repr(q.answer_text))
    q.answer_text = (
        "Define a podcast\n"
        "A podcast is a series of pre-recorded audio or video files \u2713 "
        "that a user can download or stream \u2713 to a computer or mobile "
        "device for listening/viewing"
    )
    q.marks = 2
    db.session.commit()
    print('AFTER  A:', repr(q.answer_text))
    print('AFTER  marks=', q.marks)

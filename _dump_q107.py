import sqlite3, json
from app import app, db, QuestionBankItem
with app.app_context():
    q = db.session.get(QuestionBankItem, '27f88603-cba0-407a-a63c-64895c8b1a29')
    print('marks:', q.marks)
    print('---TEXT---')
    print(repr(q.question_text))

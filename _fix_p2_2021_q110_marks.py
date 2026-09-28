from app import app, db, QuestionBankItem

with app.app_context():
    q = QuestionBankItem.query.filter(QuestionBankItem.id.like('4c9ac245%')).first()
    print('before:', q.id[:8], 'marks=', q.marks, 'type=', q.question_type)
    print('  qtext:', repr((q.question_text or '')[:120]))
    q.marks = 1  # 1.10 is a single MCQ worth 1 mark (MG: "1.10 B 1")
    db.session.commit()
    print('after: marks=', q.marks)

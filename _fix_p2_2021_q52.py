import json
from app import app, db, GeneratedPaper, QuestionBankItem

with app.app_context():
    # inspect 5.4 password item first
    q21 = QuestionBankItem.query.filter(QuestionBankItem.id.like('19cc8b2f%')).first()
    print('5.4 text:', repr(q21.question_text))

    # 5.2 stem: strip leaked "Network D", wire diagram
    q17 = QuestionBankItem.query.filter(QuestionBankItem.id.like('c2703cdb%')).first()
    q17.question_text = "Consider the diagram of a network below and answer the questions that follow."
    q17.image_path = 'uploads/cat_p2_mj21/q5_2_network.png'
    q17.image_width = 80
    tags = q17.tags or ''
    if 'noborder' not in tags:
        q17.tags = tags + ',noborder'
    db.session.commit()
    print('5.2 diagram wired; tags:', q17.tags)

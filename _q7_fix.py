import json
from app import app, db, QuestionBankItem, GeneratedPaper

PID="4cc75484-e298-41f3-bd08-e3d1db11ee71"
with app.app_context():
    p=db.session.get(GeneratedPaper,PID)
    secs=json.loads(p.sections); sec=secs[0]; qids=sec['question_ids']

    # Fix B: 7.1.3 underline "total"
    r56=db.session.get(QuestionBankItem,qids[56])
    old56=r56.question_text
    new56=old56.replace("Determine the total visits","Determine the __total__ visits")
    assert new56!=old56, "underline replace failed"
    r56.question_text=new56
    print("IDX56 old->new:")
    print("  ", repr(old56))
    print("  ", repr(new56))

    # Fix A: 7.2 stem bold "List"
    r57=db.session.get(QuestionBankItem,qids[57])
    old57=r57.question_text
    new57=old57.replace("Work in the List worksheet.","Work in the **List** worksheet.")
    assert new57!=old57, "List bold replace failed"
    r57.question_text=new57
    print("IDX57 old->new:")
    print("  ", repr(old57))
    print("  ", repr(new57))

    p.sections=json.dumps(secs,ensure_ascii=False)
    db.session.commit()
    print("COMMITTED")

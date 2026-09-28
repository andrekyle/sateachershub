import json
from app import app, db, QuestionBankItem, GeneratedPaper
with app.app_context():
    p=db.session.get(GeneratedPaper,"4cc75484-e298-41f3-bd08-e3d1db11ee71")
    secs=json.loads(p.sections); sec=secs[0]; qids=sec['question_ids']
    print("SPLITS", sec.get('splits'))
    print("QINSTR[5]:", repr(sec.get('qinstructions',[None]*6)[5]))
    print("QOUTRO[5]:", repr(sec.get('qoutros',[None]*6)[5]))
    qpt=sec.get('qpost_texts',{})
    for i in range(43,53):
        r=db.session.get(QuestionBankItem,qids[i])
        print("="*70)
        print("IDX",i,"id",qids[i],"marks",r.marks,"img",r.image_path,"w",r.image_width,"tags",r.tags)
        print("QTEXT:", repr(r.question_text))
        print("ATEXT:", repr(r.answer_text))
        if qids[i] in qpt:
            print("QPOST:", repr(qpt[qids[i]]))
        sub=sec.get('subitems',{})
        if qids[i] in sub:
            print("SUBITEM:", repr(sub[qids[i]]))

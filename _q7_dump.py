import json
from app import app, db, QuestionBankItem, GeneratedPaper
with app.app_context():
    p=db.session.get(GeneratedPaper,"4cc75484-e298-41f3-bd08-e3d1db11ee71")
    secs=json.loads(p.sections); sec=secs[0]; qids=sec['question_ids']
    print("splits", sec['splits'])
    print("qinstr[6]", repr(sec['qinstructions'][6]))
    print("qoutro[6]", repr(sec['qoutros'][6]))
    print("="*60)
    for i in range(53,60):
        r=db.session.get(QuestionBankItem,qids[i])
        print("IDX",i,"id",qids[i])
        print("  marks",r.marks,"img",r.image_path,"w",r.image_width,"tags",r.tags)
        print("  qtext:",repr(r.question_text))
        print("  atext:",repr(r.answer_text))
        post=sec.get('qpost_texts',{}).get(qids[i])
        print("  qpost:",repr(post))
        print("-"*40)
    print("subitems type", type(sec.get('subitems')))
    print("subitems", repr(sec.get('subitems')))
    print("qpost_texts keys", list(sec.get('qpost_texts',{}).keys()))

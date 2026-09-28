# -*- coding: utf-8 -*-
from app import app, db, GeneratedPaper, QuestionBankItem
import json
PID='4cc75484-e298-41f3-bd08-e3d1db11ee71'
with app.app_context():
    p=db.session.get(GeneratedPaper,PID); secs=json.loads(p.sections); sec=secs[0]
    qids=sec['question_ids']
    print('=== splits ===', sec.get('splits'))
    print('=== subitems ===', sec.get('subitems'))
    print('=== qtitles[4] ===', repr(sec.get('qtitles',[None]*5)[4] if len(sec.get('qtitles',[]))>4 else None))
    print('=== qinstructions[4] ===', repr(sec.get('qinstructions',[None]*5)[4] if len(sec.get('qinstructions',[]))>4 else None))
    qo=sec.get('qoutros',[])
    print('=== qoutros[4] ===', repr(qo[4] if len(qo)>4 else None))
    qpt=sec.get('qpost_texts',{})
    for idx in range(32,42):
        it=db.session.get(QuestionBankItem,qids[idx])
        print('\n--- idx', idx, 'qid', qids[idx][:8], 'marks=',it.marks, 'img=',repr(it.image_path),'w=',it.image_width,'tags=',repr(it.tags),'type=',it.question_type)
        print('   TEXT:', repr(it.question_text))
        if qids[idx] in qpt:
            print('   QPOST:', repr(qpt[qids[idx]]))

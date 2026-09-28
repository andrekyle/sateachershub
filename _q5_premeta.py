# -*- coding: utf-8 -*-
from app import app, db, GeneratedPaper, QuestionBankItem
import json
PID='4cc75484-e298-41f3-bd08-e3d1db11ee71'
with app.app_context():
    p=db.session.get(GeneratedPaper,PID); secs=json.loads(p.sections); sec=secs[0]
    qids=sec['question_ids']
    print('len qids', len(qids))
    print('splits', sec.get('splits'))
    print('subitems', sec.get('subitems'))
    for i in range(31,43):
        it=db.session.get(QuestionBankItem, qids[i])
        print('---- idx', i, 'qid', qids[i][:8])
        print('  type=', getattr(it,'question_type',None),'marks=',it.marks)
        print('  grade=',getattr(it,'grade',None),'subject=',getattr(it,'subject',None),'topic=',getattr(it,'topic',None),'owner=',getattr(it,'owner_id',None))
        print('  img=',getattr(it,'image_path',None),'w=',getattr(it,'image_width',None))
        print('  tags=',getattr(it,'tags',None))
        print('  qtext=',repr(it.question_text)[:200])
    print('==== qpost keys ====')
    for k,v in (sec.get('qpost_texts',{}) or {}).items():
        # only Q5-range qids
        if k in qids[31:43]:
            print(' qpost', k[:8], 'idx', qids.index(k), repr(v)[:160])

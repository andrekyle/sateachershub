from app import app, GeneratedPaper, QuestionBankItem
import json
PID = "49670bf2-0dbd-45c0-a6c1-547fa8091675"
with app.app_context():
    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    by = {q.id[:8]: q for q in QuestionBankItem.query.all()}
    secA = secs[0]
    print("SECA keys:", list(secA.keys()))
    print("splits:", secA.get('splits'))
    print("qtitles:", secA.get('qtitles'))
    print("tf_no_mark:", repr(secA.get('tf_no_mark')))
    print("tf_examples:", secA.get('tf_examples'))
    qids = secA['question_ids']
    print("nitems:", len(qids))
    for i, qid in enumerate(qids):
        it = by.get(qid[:8])
        if it is None:
            print(i, qid[:8], 'MISSING'); continue
        if i >= 20:  # Q3 region after splits[2]=20
            print('idx', i, qid[:8], 'm=', it.marks)
            print('  Q:', repr((it.question_text or '')[:160]))
            print('  A:', repr((it.answer_text or '')[:200]))

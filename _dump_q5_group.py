from app import app, db, QuestionBankItem, GeneratedPaper
import json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections) if isinstance(p.sections, str) else p.sections
    secB = secs[1]
    qids = secB['question_ids']
    splits = secB.get('splits', [])
    print('splits:', splits)
    # Q5 group: from splits[1]=16 to splits[2]=24, so items 16..23 -> 5.1..5.8
    for idx in range(16, min(24, len(qids))):
        qid = qids[idx]
        q = db.session.get(QuestionBankItem, qid)
        print(f'--- idx={idx} qid={qid} marks={q.marks}')
        print('  Qtext:', repr((q.question_text or '')[:120]))
        print('  Atext:', repr((q.answer_text or '')[:400]))

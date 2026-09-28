from app import app, db, QuestionBankItem, GeneratedPaper
import json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections) if isinstance(p.sections, str) else p.sections
    for si, sec in enumerate(secs):
        qids = sec.get('question_ids', [])
        sec_total = 0
        per_q = []
        splits = sec.get('splits') or [0]
        # Compute group totals using splits boundaries
        bounds = list(splits) + [len(qids)]
        for gi in range(len(bounds)-1):
            s, e = bounds[gi], bounds[gi+1]
            gtot = 0
            for idx in range(s, e):
                q = db.session.get(QuestionBankItem, qids[idx])
                gtot += (q.marks or 0)
            per_q.append((s, e, gtot))
            sec_total += gtot
        print(f'SEC {si} stored marks key={sec.get("marks")!r} computed total={sec_total}  groups={per_q}')

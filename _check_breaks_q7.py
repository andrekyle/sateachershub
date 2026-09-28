import json
from app import app, GeneratedPaper, db, QuestionBankItem

PID = '59936ea1-87fc-4507-8f15-4c4c77e22dfd'

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections or '[]')
    for si, sec in enumerate(secs):
        qids = sec.get('question_ids') or []
        fb = set(sec.get('forced_breaks') or [])
        if not qids:
            continue
        has_q7 = False
        rows = []
        for idx, qid in enumerate(qids):
            q = db.session.get(QuestionBankItem, qid)
            if not q:
                continue
            t = (q.question_text or '').strip().replace('\n', ' | ')
            a = (q.answer_text or '').strip().replace('\n', ' | ')
            lead = (t[:90] or a[:90]).strip()
            is_q7 = lead.startswith('7.') or lead.startswith('7 ')
            if is_q7:
                has_q7 = True
            rows.append((idx, qid, qid in fb, lead))
        if not has_q7 and not any(hit for _, _, hit, _ in rows):
            continue
        print('\nSECTION', si)
        print('forced_breaks_count:', len(fb))
        for idx, qid, hit, lead in rows:
            if hit or has_q7:
                print(idx, qid[:8], 'FORCED' if hit else '      ', lead)

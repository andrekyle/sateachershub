import json
import app as appmod
PID = "60471f83-d846-48f7-9195-629c43e3ab8f"
with appmod.app.app_context():
    p = appmod.GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections or "[]")
    sec = secs[0]
    qids = sec["question_ids"]
    items = {q.id: q for q in appmod.QuestionBankItem.query.filter(appmod.QuestionBankItem.id.in_(qids)).all()}
    print("splits=", sec.get("splits"))
    print("subitems=", sec.get("subitems"))
    print("total_marks=", p.total_marks)
    for i, qid in enumerate(qids):
        it = items.get(qid)
        t = (it.question_text or "").replace("\n", " \\n ")
        print(f"[{i:02d}] {qid} m={it.marks} img={bool(it.image_path)} :: {t[:120]}")

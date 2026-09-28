import json
import app as appmod

PID = "60471f83-d846-48f7-9195-629c43e3ab8f"
out = []
with appmod.app.app_context():
    p = appmod.GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections or "[]")
    s = secs[0]
    qids = s.get("question_ids", [])
    items = {q.id: q for q in appmod.QuestionBankItem.query.filter(appmod.QuestionBankItem.id.in_(qids)).all()}
    for idx, qid in enumerate(qids):
        q = items.get(qid)
        out.append(f"\n==== [{idx}] marks={q.marks} type={q.question_type} img={q.image_path!r} ====")
        out.append("QID=" + qid)
        out.append(repr(q.question_text))
with open("_p1_full.txt","w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote _p1_full.txt")

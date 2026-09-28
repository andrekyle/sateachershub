import json, io
from app import app, db, GeneratedPaper, QuestionBankItem

PID = "06a40eac-5b21-4ef1-815c-698cecce89f2"
out = io.StringIO()
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    sec = secs[0]
    qids = sec['question_ids']
    splits = sec.get('splits', [])
    subitems = sec.get('subitems', [])
    out.write(f"splits={splits}\nsubitems={subitems}\nn_items={len(qids)}\n")
    for idx, qid in enumerate(qids):
        q = db.session.get(QuestionBankItem, qid)
        out.write(f"\n--- idx{idx} id={qid} marks={q.marks} ---\n")
        out.write("ANSWER:\n")
        out.write(repr(q.answer_text))
        out.write("\n")
open("_memo_db_dump.txt", "w", encoding="utf-8").write(out.getvalue())
print("written _memo_db_dump.txt")

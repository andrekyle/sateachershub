import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections or '[]')
    sec = secs[0]
    qids = sec['question_ids']
    splits = sec['splits']
    subitems = set(sec.get('subitems') or [])
    # map index -> question number
    out = []
    for i, qid in enumerate(qids):
        q = db.session.get(QuestionBankItem, qid)
        marker = ''
        if i in splits:
            marker = f' <<< Q-START (split idx {splits.index(i)+1})'
        sub = ' [SUBITEM]' if i in subitems else ''
        out.append(f"--- idx {i}{marker}{sub} | id={qid} | marks={q.marks} | type={q.question_type} | topic={q.topic!r} | img={q.image_path!r}")
        out.append(f"    Q: {q.question_text!r}")
        out.append("")
    with open("_p1n23_items.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("wrote", len(qids), "items")

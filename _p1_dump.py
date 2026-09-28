import json
import app as appmod

PID = "60471f83-d846-48f7-9195-629c43e3ab8f"
out = []
with appmod.app.app_context():
    p = appmod.GeneratedPaper.query.get(PID)
    out.append(f"TITLE: {p.title}")
    out.append(f"subject={p.subject} grade={p.grade} paper_number={p.paper_number}")
    out.append(f"total_marks={p.total_marks} duration={p.duration_minutes}")
    out.append(f"exam_date={p.exam_date}")
    secs = json.loads(p.sections or "[]")
    out.append(f"NUM SECTIONS: {len(secs)}")
    # gather all qids
    allids = []
    for s in secs:
        allids += s.get("question_ids", [])
    items = {q.id: q for q in appmod.QuestionBankItem.query.filter(appmod.QuestionBankItem.id.in_(allids)).all()}
    for si, s in enumerate(secs):
        out.append(f"\n######## SECTION {si}: title={s.get('title')!r}")
        out.append(f"  instructions={s.get('instructions')!r}")
        out.append(f"  splits={s.get('splits')}")
        out.append(f"  subitems={s.get('subitems')}")
        out.append(f"  qtitles={s.get('qtitles')}")
        out.append(f"  qinstructions={s.get('qinstructions')}")
        out.append(f"  qpost_texts keys={list((s.get('qpost_texts') or {}).keys())}")
        out.append(f"  qimages={s.get('qimages')}")
        qids = s.get("question_ids", [])
        out.append(f"  NUM ITEMS: {len(qids)}")
        for idx, qid in enumerate(qids):
            q = items.get(qid)
            if not q:
                out.append(f"    [{idx}] MISSING {qid}")
                continue
            qt = (q.question_text or "").replace("\n", " \\n ")
            img = q.image_path or ""
            out.append(f"    [{idx}] marks={q.marks} type={q.question_type} img={img!r} iw={q.image_width} | {qt[:160]}")

with open("_p1_db.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote _p1_db.txt")

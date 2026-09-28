import json
import app as appmod

PID = "48c8c8d1-b356-490a-90a6-56868b67d10d"  # CAT P1 Nov 2025 (correct reference)
out = []
with appmod.app.app_context():
    p = appmod.GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections or "[]")
    s = secs[0]
    out.append("===== SCENARIO =====")
    out.append(repr(s.get('scenario')))
    out.append("\n===== SPLITS =====")
    out.append(repr(s.get('splits')))
    out.append("subitems=" + repr(s.get('subitems')))
    out.append("forced_breaks=" + repr(s.get('forced_breaks')))
    out.append("no_breaks=" + repr(s.get('no_breaks')))
    out.append("\n===== QTITLES =====")
    for i, t in enumerate(s.get('qtitles') or []):
        out.append(f"  [{i}] {t!r}")
    out.append("\n===== QINSTRUCTIONS (per-question intros) =====")
    for i, t in enumerate(s.get('qinstructions') or []):
        out.append(f"  [{i}] {t!r}")
    out.append("\n===== QPOST_TEXTS =====")
    qpt = s.get('qpost_texts') or {}
    qids = s.get('question_ids', [])
    items = {q.id: q for q in appmod.QuestionBankItem.query.filter(appmod.QuestionBankItem.id.in_(qids)).all()}
    for k, v in qpt.items():
        # find idx
        idx = qids.index(k) if k in qids else '?'
        out.append(f"  qid idx={idx}: {v!r}")
    out.append("\n===== ITEMS (with image_path) =====")
    for idx, qid in enumerate(qids):
        q = items.get(qid)
        if not q: 
            out.append(f"  [{idx}] MISSING"); continue
        qt = (q.question_text or '').replace('\n',' \\n ')[:90]
        out.append(f"  [{idx}] m={q.marks} type={q.question_type} img={q.image_path!r} iw={q.image_width} | {qt}")

with open("_p1ref.txt","w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote _p1ref.txt")

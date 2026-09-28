"""Dump current state of CAT P1 May/June 2023 paper + per-question item details."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '4cc75484-e298-41f3-bd08-e3d1db11ee71'

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    print("=== PAPER META ===")
    print("title:", p.title)
    print("subject:", p.subject, "| grade:", p.grade)
    print("total_marks:", p.total_marks, "| duration:", p.duration_minutes)
    print("paper_number:", p.paper_number, "| exam_date:", p.exam_date)
    print("cover_subtitle:", repr(p.cover_subtitle))
    print("sub_header:", repr(p.sub_header))
    print("cover_extra_note:", repr(p.cover_extra_note))
    print("logo_path:", p.logo_path)
    print("instructions (first 400):", repr((p.instructions or '')[:400]))
    secs = json.loads(p.sections)
    print("\n=== SECTIONS COUNT:", len(secs), "===")
    sec = secs[0]
    print("section keys:", list(sec.keys()))
    qids = sec.get('question_ids', [])
    splits = sec.get('splits', [])
    print("num items:", len(qids))
    print("splits:", splits)
    print("subitems:", sec.get('subitems'))
    print("qtitles:", sec.get('qtitles'))
    print("qoutros:", sec.get('qoutros'))
    print("scenario:", repr(sec.get('scenario'))[:300])
    qinstr = sec.get('qinstructions', [])
    print("\n=== QINSTRUCTIONS ===")
    for i, qi in enumerate(qinstr):
        print(f"  [{i}]:", repr(qi)[:200])
    # build per-Q boundaries
    bounds = splits + [len(qids)]
    print("\n=== ITEMS PER QUESTION ===")
    qpost = sec.get('qpost_texts', {})
    qimgs_keys = sec.get('qimages', [])
    for qn in range(len(splits)):
        a = splits[qn]
        b = bounds[qn+1]
        print(f"\n--- QUESTION {qn+1}  items[{a}:{b}] ---")
        for idx in range(a, b):
            qid = qids[idx]
            it = db.session.get(QuestionBankItem, qid)
            if not it:
                print(f"  idx{idx} {qid} MISSING")
                continue
            txt = (it.question_text or '').replace('\n', ' / ')
            print(f"  idx{idx} m={it.marks} img={it.image_path} w={it.image_width} tags={it.tags}")
            print(f"        Q: {txt[:160]}")
            if qid in qpost:
                print(f"        POST: {repr(qpost[qid])[:120]}")

import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    print("TITLE:", p.title)
    print("total_marks:", p.total_marks)
    print("paper_number:", p.paper_number)
    print("exam_date:", p.exam_date)
    print("duration_minutes:", getattr(p, 'duration_minutes', None))
    print("cover_subtitle:", repr(getattr(p, 'cover_subtitle', None)))
    print("sub_header:", repr(getattr(p, 'sub_header', None)))
    print("cover_extra_note:", repr(getattr(p, 'cover_extra_note', None)))
    print("school_name:", repr(getattr(p, 'school_name', None)))
    print("\n--- INSTRUCTIONS ---")
    print(repr(p.instructions))
    secs = json.loads(p.sections or '[]')
    print("\nNUM SECTIONS:", len(secs))
    for si, sec in enumerate(secs):
        print(f"\n===== SECTION {si}: title={sec.get('title')!r} =====")
        print("  keys:", list(sec.keys()))
        print("  splits:", sec.get('splits'))
        print("  subitems:", sec.get('subitems'))
        print("  qtitles:", sec.get('qtitles'))
        qins = sec.get('qinstructions')
        print("  qinstructions count:", len(qins) if qins else 0)
        if qins:
            for gi, qi in enumerate(qins):
                print(f"    [{gi}] {qi!r}")
        print("  qimages:", sec.get('qimages'))
        print("  qpost_texts keys:", list((sec.get('qpost_texts') or {}).keys()))
        qids = sec.get('question_ids', [])
        print("  num question_ids:", len(qids))

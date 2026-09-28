import json
from app import app, db, GeneratedPaper

MJ24 = '1b9d1110-e5f8-46ec-9178-e1a214094853'
with app.app_context():
    p = db.session.get(GeneratedPaper, MJ24)
    print("=== cover_subtitle:", repr(p.cover_subtitle))
    print("=== sub_header:", repr(p.sub_header))
    print("=== cover_extra_note:", repr(p.cover_extra_note))
    print("=== total_marks:", p.total_marks)
    print("\n=== INSTRUCTIONS ===")
    print(p.instructions)
    secs = json.loads(p.sections or '[]')
    sec = secs[0]
    print("\n=== qtitles:", sec.get('qtitles'))
    print("\n=== qinstructions ===")
    for gi, qi in enumerate(sec.get('qinstructions') or []):
        print(f"\n--- [{gi}] ---")
        print(qi)

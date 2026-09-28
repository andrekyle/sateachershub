from app import app, db, GeneratedPaper
import json, re
OWNER = '951c278b-2d76-4969-b0d4-6271479bf397'
PID = '9cacaaa0-c251-43c7-9837-4524b68031f0'  # CAT P2 May-June 2022 (has match-block)
with app.app_context():
    gp = GeneratedPaper.query.get(PID)
    secs = json.loads(gp.sections)
    all_qids = []
    for s in secs:
        all_qids += (s.get('question_ids') or [])
    print('total question_ids in editor sections:', len(all_qids))

    c = app.test_client()
    with c.session_transaction() as ss:
        ss['_user_id'] = OWNER; ss['_fresh'] = True
    html = c.get(f'/teacher/generator/{PID}/preview?embed=1').get_data(as_text=True)
    rowqids = re.findall(r'data-row-qid="([^"]+)"', html)
    uniq = list(dict.fromkeys(rowqids))
    print('unique preview data-row-qids:', len(uniq))
    missing = [q for q in uniq if q not in all_qids]
    print('row-qids NOT present in editor question_ids:', len(missing))
    for q in missing[:20]:
        print('  MISSING', q)
    # also show the match-block data-qids attr
    m = re.search(r'data-qids="([^"]+)"', html)
    if m:
        dq = m.group(1).split()
        print('match-block data-qids count:', len(dq), '| all in question_ids:', all(x in all_qids for x in dq))

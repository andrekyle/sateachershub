"""Dump Q8 items (Section B) of the P2 2025 paper so we can attach images
and restructure body/post_text.
"""
from app import app, db, GeneratedPaper

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

with app.app_context():
    paper = db.session.get(GeneratedPaper, PAPER_ID)
    secs = paper.sections
    # Section B is index 1 (A=0, B=1, C=2). Confirm by title.
    for si, sec in enumerate(secs):
        print('SECTION', si, '->', sec.get('title'))
    print('=' * 60)
    secB = secs[1]
    qs = secB.get('questions', [])
    for i, q in enumerate(qs):
        if i < 40:
            continue
        qid = q.get('id')
        txt = (q.get('question_text') or '').replace('\n', ' \\n ')
        print(f'[idx {i}] id={qid}')
        print(f'   marks={q.get("marks")} type={q.get("question_type")} img={q.get("image_path")!r} w={q.get("image_width")}')
        print(f'   text={txt[:300]}')
        pt = q.get('post_text')
        if pt:
            print(f'   post_text={pt!r}')
        print('-' * 40)

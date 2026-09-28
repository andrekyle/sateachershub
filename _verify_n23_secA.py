import app as A
with A.app.app_context():
    paper = A.GeneratedPaper.query.filter_by(title='CAT P2 Nov 2023').first()
    ctx = A._build_paper_context(paper, with_memo=False, version='current')
    secA = ctx['sections'][0]
    for grp in secA['qgroups']:
        print(f"QUESTION {grp['qn']}: {grp.get('title','')!r}")
        instr = (grp.get('instructions') or '').strip()
        print('   instr:', instr[:120] + ('...' if len(instr) > 120 else ''))

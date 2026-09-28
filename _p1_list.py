import json
import app as appmod

with appmod.app.app_context():
    papers = appmod.GeneratedPaper.query.filter(
        appmod.GeneratedPaper.subject.like('%Computer Applications%'),
        appmod.GeneratedPaper.paper_number == 1
    ).all()
    for p in papers:
        secs = json.loads(p.sections or "[]")
        print(f"{p.id} | {p.title} | exam_date={p.exam_date} | secs={len(secs)}")
        for s in secs:
            sc = s.get('scenario')
            print(f"    sec title={s.get('title')!r} scenario={(sc[:60] if sc else None)!r}")
            print(f"      qtitles={s.get('qtitles')}")
            print(f"      qinstructions={[ (x[:40] if x else x) for x in (s.get('qinstructions') or [])]}")
            print(f"      qoutros={s.get('qoutros')}")
            print(f"      keys={sorted(s.keys())}")

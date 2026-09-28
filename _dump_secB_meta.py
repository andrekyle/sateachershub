from app import app, db, GeneratedPaper
import json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections) if isinstance(p.sections, str) else p.sections
    secB = secs[1]
    for k, v in secB.items():
        if isinstance(v, list):
            print(f'  {k}: list len={len(v)}')
            if k in ('qtitles','qinstructions','qoutros','qmemo_notes','splits','forced_breaks','no_breaks'):
                for i, item in enumerate(v):
                    print(f'    [{i}] {item!r}')
        elif isinstance(v, dict):
            print(f'  {k}: dict keys={list(v.keys())}')
        else:
            print(f'  {k}: {v!r}')

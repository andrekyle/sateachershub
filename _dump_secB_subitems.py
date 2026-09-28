from app import app, db, GeneratedPaper
import json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections) if isinstance(p.sections, str) else p.sections
    secB = secs[1]
    print('subitems:')
    for i, item in enumerate(secB.get('subitems') or []):
        print(f'  [{i}] {item!r}')
    print('\nqpost_texts:')
    for k, v in (secB.get('qpost_texts') or {}).items():
        print(f'  {k}: {v!r}')

"""Inspect Section B item idx0 (4.1 intro) and idx43 (8.4, has image) structure."""
import json
from app import app, db, GeneratedPaper

PID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = p.sections if isinstance(p.sections, list) else json.loads(p.sections)
    secB = secs[1]
    items = secB.get('items') or secB.get('questions') or []
    print('section keys:', list(secB.keys()))
    print('num items:', len(items))
    for idx in (0, 43, 45):
        print('\n===== idx', idx, '=====')
        print(json.dumps(items[idx], indent=2, ensure_ascii=False)[:1500])

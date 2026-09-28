"""Inspect the shape of paper.sections for the P2 2025 paper."""
import json
from app import app, db, GeneratedPaper

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

with app.app_context():
    paper = db.session.get(GeneratedPaper, PAPER_ID)
    secs = paper.sections
    print('type(sections)=', type(secs))
    if isinstance(secs, str):
        secs = json.loads(secs)
        print('parsed json, type now', type(secs), 'len', len(secs))
    print('top-level keys/sample:')
    print(json.dumps(secs, indent=2)[:1500])

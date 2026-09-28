# -*- coding: utf-8 -*-
import json
from app import app, db, GeneratedPaper

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    sec = secs[0]
    print("section keys:", list(sec.keys()))
    for k in ('intro', 'scenario', 'preamble', 'section_intro', 'intro_text', 'qinstructions'):
        if k in sec:
            v = sec[k]
            print(f"\n[{k}] =", repr(v)[:400])

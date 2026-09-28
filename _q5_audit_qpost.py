# -*- coding: utf-8 -*-
from app import app, db, GeneratedPaper
import json, re
PID='4cc75484-e298-41f3-bd08-e3d1db11ee71'
with app.app_context():
    p=db.session.get(GeneratedPaper,PID); secs=json.loads(p.sections)
    for si,sec in enumerate(secs):
        qpt=sec.get('qpost_texts',{}) or {}
        for qid,txt in qpt.items():
            if not txt: continue
            multiline = ('\n' in txt.strip())
            trailing = bool(re.search(r'\(\d{1,3}\)\s*$', txt))
            anymark = bool(re.search(r'\(\d{1,3}\)', txt))
            flag = 'MULTILINE+TRAILMARK' if (multiline and trailing) else ('MULTILINE+INLINEMARK' if (multiline and anymark) else '')
            if multiline and anymark:
                print(f'sec{si} qid={qid[:8]} trailing={trailing} {flag}')
                print('   ', repr(txt))

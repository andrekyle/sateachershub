# -*- coding: utf-8 -*-
import json
from app import app, db, GeneratedPaper

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
SCENARIO = ("Different types of transportation are used for moving people and goods "
            "from one point to another. Although many people use public transportation, "
            "cars have become more popular over the years.")
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    secs[0]['scenario'] = SCENARIO
    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    print("scenario set:", secs[0]['scenario'][:60], "...")

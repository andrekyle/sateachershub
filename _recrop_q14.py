# -*- coding: utf-8 -*-
import os, json
import pdfplumber
from app import app, db, GeneratedPaper, QuestionBankItem
PID = '2b687490-9157-4e10-b0c9-2bab1ee303fd'
QP = r"static\uploads\Computer Application Technology P1 Nov 2021 Eng.pdf"
OUT = r"static\uploads\cat_p1_nov21"

with pdfplumber.open(QP) as pdf:
    pg = pdf.pages[3]
    pg.within_bbox((85, 490, 527.5, 766.5)).to_image(resolution=220).save(os.path.join(OUT, 'q1_4_textbox.png'))
print('re-cropped q1_4_textbox.png with frame')

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    qids = json.loads(p.sections)[0]['question_ids']
    q = db.session.get(QuestionBankItem, qids[3])
    q.image_width = 92
    tags = [t for t in (q.tags or '').split(',') if t.strip()]
    if 'noborder' not in tags:
        tags.append('noborder')
    q.tags = ','.join(tags)
    db.session.commit()
    print('idx3 tags=', q.tags, 'width=', q.image_width)

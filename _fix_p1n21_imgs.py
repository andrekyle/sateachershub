# -*- coding: utf-8 -*-
import os, json
import pdfplumber
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '2b687490-9157-4e10-b0c9-2bab1ee303fd'
QP = r"static\uploads\Computer Application Technology P1 Nov 2021 Eng.pdf"
OUT = r"static\uploads\cat_p1_nov21"
os.makedirs(OUT, exist_ok=True)

# (item_index, filename, page_idx, bbox, width)
JOBS = [
 (3,  'q1_4_textbox.png',   3, (92.8, 492.8, 519.3, 764.7), 55),
 (5,  'q1_6_multilevel.png',4, (91.4, 251.3, 516.6, 588.1), 78),
 (11, 'q2_2_toc.png',       5, (94.8, 242.4, 519.2, 386.4), 80),
 (32, 'q4_6_chart.png',     9, (124.4,115.7, 482.9, 332.4), 72),
 (42, 'q5_6_report.png',   11, (96.4, 403.4, 520.1, 658.4), 80),
 (43, 'q6_1_webpage.png',  12, (50.5, 268.3, 572.2, 784.0), 88),
 (48, 'q6_2_webpage.png',  13, (48.2, 427.8, 546.0, 658.4), 80),
]

with pdfplumber.open(QP) as pdf:
    for _, fn, pi, bbox, _w in JOBS:
        page = pdf.pages[pi]
        # clamp bbox to page
        x0, top, x1, bot = bbox
        x1 = min(x1, float(page.width)); bot = min(bot, float(page.height))
        im = page.within_bbox((x0, top, x1, bot)).to_image(resolution=220)
        im.save(os.path.join(OUT, fn))
        print('cropped', fn)

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    qids = json.loads(p.sections)[0]['question_ids']
    for i, fn, _pi, _bb, w in JOBS:
        q = db.session.get(QuestionBankItem, qids[i])
        q.image_path = 'uploads/cat_p1_nov21/' + fn
        q.image_width = w
        # let CSS draw the black border (no 'noborder' tag)
        q.tags = (q.tags or '')
        print('wired idx', i, fn, 'w', w)
    db.session.commit()
    print('done')

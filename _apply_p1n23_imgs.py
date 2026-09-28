# -*- coding: utf-8 -*-
"""Extract the 9 example screenshots from the CAT P1 Nov 2023 PDF into
static/uploads/cat_p1_nov23/ and attach them to the matching QuestionBankItems."""
import os, json, fitz
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
PDF = r"static/uploads/Computer Applications Technology P1 Nov 2023 Eng.pdf"
OUTDIR = r"static/uploads/cat_p1_nov23"
os.makedirs(OUTDIR, exist_ok=True)

# idx -> (pdf_page_index, xref, out_filename, width_percent)
SPEC = {
    1:  (3,  35, "q1_2_heading.png",  72),
    4:  (4,  38, "q1_5_table.png",    52),
    6:  (4,  39, "q1_7_letterD.png",  80),
    18: (5,  48, "q2_6_shape.png",    72),
    19: (6,  51, "q2_7_smartart.png", 60),
    30: (9,  60, "q4_6_chart.png",    62),
    41: (12, 71, "q6_1_webpage.png",  72),
    47: (14, 76, "q6_2_webpage.png",  82),
    48: (15, 79, "q7_1_logo.png",     34),
}

doc = fitz.open(PDF)
saved = {}
for idx, (pno, xref, fn, w) in SPEC.items():
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha >= 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    path = os.path.join(OUTDIR, fn)
    pix.save(path)
    saved[idx] = (fn, w)
    print("saved", path, f"{pix.width}x{pix.height}")

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    qids = secs[0]['question_ids']
    for idx, (fn, w) in saved.items():
        q = db.session.get(QuestionBankItem, qids[idx])
        q.image_path = f"uploads/cat_p1_nov23/{fn}"
        q.image_width = w
        q.image_offset = 0
        tags = [t.strip() for t in (q.tags or '').split(',') if t.strip()]
        if 'noborder' not in tags:
            tags.append('noborder')
        q.tags = ', '.join(tags)
    db.session.commit()
    print("DONE attached", len(saved), "images")

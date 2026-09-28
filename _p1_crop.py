import pdfplumber, os

PDF = r"data/all_uploads/Computer Applications Technology P1 May-June 2025 Eng.pdf"
OUTDIR = r"static/uploads/cat_p1_mj25"
os.makedirs(OUTDIR, exist_ok=True)

# (filename, page(1-based), (x0, top, x1, bottom)) with small padding
CROPS = [
    ("q1_8_smartart.png",  6, (96, 165, 532, 412)),
    ("q1_11_table.png",    6, (157, 581, 476, 717)),
    ("q2_4.png",           7, (196, 404, 393, 589)),
    ("q3_2_headings.png",  8, (99, 415, 534, 480)),
    ("q4_5_chart.png",     10, (98, 178, 539, 502)),
    ("q5_1_3_location.png",11, (243, 384, 331, 523)),
    ("q5_2_form.png",      12, (100, 180, 535, 506)),
    ("q5_5_query.png",     13, (209, 121, 424, 273)),
    ("q5_7_report.png",    14, (84, 149, 543, 462)),
    ("q6_1_web.png",       15, (67, 297, 537, 781)),
    ("q6_2_web.png",       17, (156, 179, 475, 367)),
    ("q7_4_web.png",       19, (194, 176, 425, 531)),
]

with pdfplumber.open(PDF) as pdf:
    for fn, pno, bbox in CROPS:
        page = pdf.pages[pno-1]
        # clamp bbox to page
        x0, top, x1, bottom = bbox
        x1 = min(x1, page.width); bottom = min(bottom, page.height)
        im = page.crop((x0, top, x1, bottom)).to_image(resolution=400)
        path = os.path.join(OUTDIR, fn)
        im.save(path)
        print("saved", path)
print("done")

import os
import pdfplumber
PDF = r"data/all_uploads/Computer Applications Technology P2 May-June 2024 Eng.pdf"
OUT = r"static/uploads/cat_p2_mj24"
jobs = [
    (11, (153, 267, 459, 350), "q8_3_query1.png"),   # Image51 grid only
    (11, (153, 380, 459, 463), "q8_3_query2.png"),   # Image52 grid only
]
with pdfplumber.open(PDF) as pdf:
    for pi, bbox, fn in jobs:
        pg = pdf.pages[pi]
        pg.within_bbox(bbox).to_image(resolution=300).save(os.path.join(OUT, fn))
        print("saved", fn)
# remove url image (already text in DB)
u = os.path.join(OUT, "q9_3_url.png")
if os.path.exists(u):
    os.remove(u); print("removed url img")
print("done")

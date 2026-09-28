import os
import pdfplumber
PDF = r"data/all_uploads/Computer Applications Technology P2 May-June 2024 Eng.pdf"
OUT = r"static/uploads/cat_p2_mj24"
os.makedirs(OUT, exist_ok=True)

# (page_index, bbox(x0,top,x1,bottom), filename)
jobs = [
    (8,  (110, 248, 508, 465), "q6_3_report.png"),       # Image42 PAT report extract
    (10, (132, 386, 489, 586), "q8_2_html.png"),          # Image47 HTML CODE
    (10, (133, 621, 488, 780), "q8_2_webpage.png"),       # Image48 WEB PAGE
    (11, (150, 262, 462, 353), "q8_3_query1.png"),        # Image51 Query 1
    (11, (150, 375, 463, 467), "q8_3_query2.png"),        # Image52 Query 2
    (12, (443, 124, 512, 188), "q9_robot_icon.png"),      # Image55 robotics icon
    (13, (154, 297, 508, 350), "q9_3_url.png"),           # Image58 URL
]
with pdfplumber.open(PDF) as pdf:
    for pi, bbox, fn in jobs:
        pg = pdf.pages[pi]
        pg_bbox = (max(0,bbox[0]), max(0,bbox[1]), min(pg.width,bbox[2]), min(pg.height,bbox[3]))
        pg.within_bbox(pg_bbox).to_image(resolution=300).save(os.path.join(OUT, fn))
        print("saved", fn)
print("done")

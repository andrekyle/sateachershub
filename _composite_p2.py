import os
import pdfplumber
from PIL import Image
PDF = r"data/all_uploads/Computer Applications Technology P2 May-June 2024 Eng.pdf"
OUT = r"static/uploads/cat_p2_mj24"
os.makedirs(OUT, exist_ok=True)

def crop(pi, bbox, fn, res=300):
    with pdfplumber.open(PDF) as pdf:
        pdf.pages[pi].within_bbox(bbox).to_image(resolution=res).save(os.path.join(OUT, fn))

def vstack(parts, out, gap=18, bg=(255,255,255)):
    imgs = [Image.open(os.path.join(OUT, p)).convert("RGB") for p in parts]
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + gap*(len(imgs)-1)
    canvas = Image.new("RGB", (w, h), bg)
    y = 0
    for im in imgs:
        canvas.paste(im, (0, y))
        y += im.height + gap
    canvas.save(os.path.join(OUT, out))

# Q8.2 parts (label + screenshot), left-aligned at the label x
crop(10, (100, 360, 490, 586), "_q82_html.png")     # HTML CODE: + Image47
crop(10, (100, 595, 490, 778), "_q82_web.png")       # WEB PAGE: + Image48
vstack(["_q82_html.png", "_q82_web.png"], "q8_2_combined.png", gap=22)

# Q8.3.3 parts (Query label + grid)
crop(11, (150, 250, 462, 353), "_q833_q1.png")       # Query 1 + Image51
crop(11, (150, 362, 462, 466), "_q833_q2.png")       # Query 2 + Image52
vstack(["_q833_q1.png", "_q833_q2.png"], "q8_3_combined.png", gap=20)

# cleanup intermediates
for f in ("_q82_html.png","_q82_web.png","_q833_q1.png","_q833_q2.png",
          "q8_2_html.png","q8_2_webpage.png","q8_3_query1.png","q8_3_query2.png"):
    p = os.path.join(OUT, f)
    if os.path.exists(p): os.remove(p)
print("done")

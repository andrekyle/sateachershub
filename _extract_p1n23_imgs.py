# -*- coding: utf-8 -*-
"""Extract embedded example images (non-cover) to a temp folder for viewing."""
import os, fitz

PDF = r"static/uploads/Computer Applications Technology P1 Nov 2023 Eng.pdf"
OUT = r"_p1n23_imgtmp"
os.makedirs(OUT, exist_ok=True)
doc = fitz.open(PDF)
# pages with example screenshots (0-based): 3,4,5,6,9,12,14
targets = [3, 4, 5, 6, 9, 12, 14]
for pno in targets:
    page = doc[pno]
    for img in page.get_images(full=True):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        if pix.n - pix.alpha >= 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        fn = os.path.join(OUT, f"p{pno+1}_x{xref}.png")
        pix.save(fn)
        print("saved", fn, f"{pix.width}x{pix.height}")

# -*- coding: utf-8 -*-
import os, fitz
PDF = r"static/uploads/Computer Applications Technology P1 Nov 2023 Eng.pdf"
OUT = r"_p1n23_imgtmp"
doc = fitz.open(PDF)
for pno in (15, 13, 14):
    page = doc[pno]
    for img in page.get_images(full=True):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        if pix.n - pix.alpha >= 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        fn = os.path.join(OUT, f"chk_p{pno+1}_x{xref}.png")
        pix.save(fn)
        print("saved", fn, f"{pix.width}x{pix.height}")

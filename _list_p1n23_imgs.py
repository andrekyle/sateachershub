# -*- coding: utf-8 -*-
"""List embedded images per page in the CAT P1 Nov 2023 PDF."""
import fitz  # PyMuPDF

PDF = r"static/uploads/Computer Applications Technology P1 Nov 2023 Eng.pdf"
doc = fitz.open(PDF)
print("pages:", doc.page_count)
for pno in range(doc.page_count):
    page = doc[pno]
    imgs = page.get_images(full=True)
    if not imgs:
        continue
    print(f"\n--- page index {pno} (PDF page {pno+1}) : {len(imgs)} images ---")
    for img in imgs:
        xref = img[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        for r in rects:
            print(f"  xref={xref} w={img[2]} h={img[3]} rect=({r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f}) size={r.width:.0f}x{r.height:.0f}")

"""Extract embedded raster images from PDF page 7 (the StellarX advertisement)."""
import os
import fitz  # PyMuPDF

PDF = 'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'
OUT = '_q4_ad_imgs'
os.makedirs(OUT, exist_ok=True)

doc = fitz.open(PDF)
page = doc[6]  # 0-indexed page 7
imgs = page.get_images(full=True)
print('images on page 7:', len(imgs))
for i, img in enumerate(imgs):
    xref = img[0]
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha >= 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    out = os.path.join(OUT, f'img_{i}_xref{xref}.png')
    pix.save(out)
    print(f'  saved {out}  {pix.width}x{pix.height}')

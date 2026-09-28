"""Extract images embedded on page 11 (CAT P2 Nov 2025): Q8.3 grade table + Q8.5 db fields table."""
import fitz, os
src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
doc = fitz.open(src)
page = doc[10]  # page 11
imgs = page.get_images(full=True)
print(f"Page 11 has {len(imgs)} images")
for i, im in enumerate(imgs):
    xref = im[0]
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha > 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    fn = os.path.join(out_dir, f"_page11_img_{i}.png")
    pix.save(fn)
    print(f"  [{i}] xref={xref} size={pix.width}x{pix.height} -> {fn}")

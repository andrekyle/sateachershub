"""Extract images and full preview from page 13 (Q9 SECTION C / INTEGRATED SCENARIO)."""
import fitz, os
src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
doc = fitz.open(src)
page = doc[12]  # page 13
print(f"Page 13 size: {page.rect}")
imgs = page.get_images(full=True)
print(f"Page 13 has {len(imgs)} images")
for i, im in enumerate(imgs):
    xref = im[0]
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha > 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    fn = os.path.join(out_dir, f"_page13_img_{i}.png")
    pix.save(fn)
    print(f"  [{i}] xref={xref} size={pix.width}x{pix.height} -> {fn}")
# Also render the area containing the Quotation 1/2 box for visual reference
pix = page.get_pixmap(dpi=180)
pix.save(os.path.join(out_dir, "_page13_full.png"))
print("Saved _page13_full.png")

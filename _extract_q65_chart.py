"""Extract chart image from page 9 of CAT P2 Nov 2025 PDF for Q6.5."""
import fitz, os
src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
os.makedirs(out_dir, exist_ok=True)
doc = fitz.open(src)
page = doc[8]  # page 9 (0-indexed)
# Render full page as a quick reference
pix_full = page.get_pixmap(dpi=180)
pix_full.save(os.path.join(out_dir, "_page9_preview.png"))
print(f"Page 9 size: {page.rect}")
# List images on page
imgs = page.get_images(full=True)
print(f"Images found on page 9: {len(imgs)}")
for i, im in enumerate(imgs):
    xref = im[0]
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha > 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    fn = os.path.join(out_dir, f"_page9_img_{i}.png")
    pix.save(fn)
    print(f"  [{i}] xref={xref} size={pix.width}x{pix.height} -> {fn}")

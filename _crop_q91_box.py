"""Crop the Quotation 1 / Quotation 2 comparison box from the rendered page 13 of the PDF.

Approach: render page 13 at high DPI (300), then crop the bbox covering the
two side-by-side outlined boxes. Coordinates discovered by inspecting the
PDF text layout: the box sits roughly between y=170-460 and spans x=110-790
at 300 dpi (page is 2480x3508 portrait at 300 dpi).
"""
import fitz, os
from PIL import Image

src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
doc = fitz.open(src)
page = doc[12]  # page 13

# Render at 300 dpi
dpi = 300
pix = page.get_pixmap(dpi=dpi)
tmp = os.path.join(out_dir, "_p13_300.png")
pix.save(tmp)
print(f"Rendered {tmp} size={(pix.width, pix.height)}")

# Find Q9 box by searching for "Quotation 1" + "Quotation 2" text rects
results1 = page.search_for("Quotation 1")
results2 = page.search_for("Quotation 2")
results_end = page.search_for("9.1.1")  # 9.1.1 sits BELOW the box
print("Quotation 1 rects:", results1)
print("Quotation 2 rects:", results2)
print("9.1.1 rects:", results_end)

# Build crop rect: top = top of "Quotation 1" header minus padding,
# bottom = top of "9.1.1" minus padding
# left = small margin from page left, right = small margin from page right
if results1 and results_end:
    page_h = page.rect.height
    page_w = page.rect.width
    top_pt = min(r.y0 for r in results1) - 8
    bottom_pt = min(r.y0 for r in results_end) - 10
    # Find left/right by scanning paths? Use generous margins (60pt each side)
    left_pt = 100
    right_pt = page_w - 60
    print(f"Crop pts: ({left_pt},{top_pt}) -> ({right_pt},{bottom_pt})")
    # Convert pts -> pixels at chosen dpi (1pt = dpi/72 px)
    scale = dpi / 72.0
    img = Image.open(tmp)
    box = (int(left_pt * scale), int(top_pt * scale), int(right_pt * scale), int(bottom_pt * scale))
    crop = img.crop(box)
    dst = os.path.join(out_dir, "q9_1.png")
    crop.save(dst)
    print(f"Saved {dst} size={crop.size}")
else:
    print("Couldn't locate Quotation 1 or 9.1.1 — aborting.")

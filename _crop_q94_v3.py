"""Recrop q9_4 with row-numbers visible (extend left) and full row 8."""
import fitz, os
from PIL import Image

src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
doc = fitz.open(src)
page = doc[13]

stem_end = page.search_for("An incomplete spreadsheet")[0].y1
sums_top = page.search_for("To calculate")[0].y0

top_pt    = stem_end + 18
bottom_pt = sums_top - 2     # extend down a touch
left_pt   = 122              # was 140 — pull left to include row-number gutter
right_pt  = page.rect.width - 60
print(f"crop pts: L={left_pt} T={top_pt} R={right_pt} B={bottom_pt}")

dpi = 300
pix = page.get_pixmap(dpi=dpi)
tmp = os.path.join(out_dir, "_p14_tmp.png")
pix.save(tmp)
scale = dpi / 72.0
img = Image.open(tmp)
box = (int(left_pt*scale), int(top_pt*scale), int(right_pt*scale), int(bottom_pt*scale))
crop = img.crop(box)
dst = os.path.join(out_dir, "q9_4.png")
crop.save(dst)
print(f"Saved {dst} size={crop.size}")
try: os.remove(tmp)
except Exception: pass

"""Re-crop q9_1.png with full box borders visible."""
import fitz, os
from PIL import Image

src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
doc = fitz.open(src)
page = doc[12]

dpi = 300
pix = page.get_pixmap(dpi=dpi)
tmp = os.path.join(out_dir, "_p13_tmp.png")
pix.save(tmp)

# Locate landmarks
top_rect = page.search_for("Quotation 1")[0]            # very top of box headers
last_left  = page.search_for("Scratch software")[0]     # last bullet left col
last_right = page.search_for("MakeCode software")[0]    # last bullet right col
print("top:", top_rect, "last_left:", last_left, "last_right:", last_right)

# Padding: 10pt above headers, 22pt below last bullet line, generous L/R margins.
top_pt    = top_rect.y0 - 4
bottom_pt = max(last_left.y1, last_right.y1) + 22
left_pt   = 60
right_pt  = page.rect.width - 35
print(f"crop pts: L={left_pt} T={top_pt} R={right_pt} B={bottom_pt}")

scale = dpi / 72.0
img = Image.open(tmp)
box = (int(left_pt*scale), int(top_pt*scale), int(right_pt*scale), int(bottom_pt*scale))
crop = img.crop(box)
dst = os.path.join(out_dir, "q9_1.png")
crop.save(dst)
print(f"Saved {dst} size={crop.size}")

# Cleanup
try: os.remove(tmp)
except Exception: pass

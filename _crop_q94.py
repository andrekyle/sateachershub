"""Crop the Q9.4 spreadsheet table on page 14."""
import fitz, os
from PIL import Image

src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
doc = fitz.open(src)
page = doc[13]  # page 14

# Find table corners
top_q94   = page.search_for("9.4")[0]                  # 9.4 label sits left of stem
top_hdr   = page.search_for("Coding and Robotics Club") # may be empty
monday    = page.search_for("Monday")
total_time= page.search_for("Total time")
sums_para = page.search_for("To calculate the total")
print("9.4:", top_q94)
print("Coding and Robotics Club:", top_hdr)
print("Monday:", monday)
print("Total time:", total_time)
print("To calculate ...:", sums_para)

# Top of the table = a few pts above Monday
top_pt = (monday[0].y0 - 18) if monday else 200
# Bottom of the table = just below 'Total time' row label (= y1 + ~10pt)
bottom_pt = (total_time[0].y1 + 14) if total_time else 380
# Left/right margins
left_pt = 130
right_pt = page.rect.width - 130
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

"""Find the Q9.4 spreadsheet on pages 13-15 and crop it.

The Q9.4 image is the 'Coding and Robotics Club' weekly hours table.
"""
import fitz, os
from PIL import Image

src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
doc = fitz.open(src)

# Search for the anchor text on each page
for pno in range(12, 16):
    page = doc[pno]
    a = page.search_for("Coding and Robotics Club")
    b = page.search_for("#NAME?")
    c = page.search_for("9.4.1")
    print(f"page {pno+1}: 'Coding and Robotics Club'={len(a)} '#NAME?'={len(b)} '9.4.1'={len(c)}")
    if a:
        print("  ", a[0])
    if c:
        print("  9.4.1 at:", c[0])

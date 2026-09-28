"""Crop the three Q8 figures from the rendered PDF pages and save to the
p2_2025 image folder. Coordinates are fractions of page width/height; tune
then re-run if needed.
"""
import os
from PIL import Image

OUT_DIR = os.path.join('static', 'uploads', 'paper_images', 'p2_2025')
os.makedirs(OUT_DIR, exist_ok=True)

# (source png, output name, (x0, y0, x1, y1) as fractions)
CROPS = [
    ('_p2_page12.png', 'q8_4_linked_object.png', (0.315, 0.293, 0.735, 0.388)),
    ('_p2_page12.png', 'q8_6_vlookup.png',       (0.228, 0.567, 0.825, 0.730)),
    ('_p2_page13.png', 'q8_7_html_web.png',      (0.125, 0.150, 0.912, 0.425)),
]

for src, name, (x0, y0, x1, y1) in CROPS:
    im = Image.open(src)
    W, H = im.size
    box = (int(W * x0), int(H * y0), int(W * x1), int(H * y1))
    crop = im.crop(box)
    out = os.path.join(OUT_DIR, name)
    crop.save(out)
    print('wrote', out, crop.size)

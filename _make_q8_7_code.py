"""Render the 8.7 HTML code block as a bordered monospace PNG."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r"static\uploads\cat_p2_n25\q8_7.png"
LINES = [
    '<img src = "Well done" alt = "Top achiever" width = "100" height = "75" />',
    '<a href = "#Stars"> They brought us pride </a>',
]

# Fonts
try:
    f_code = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 18)
except Exception:
    f_code = ImageFont.load_default()

# Measure
pad_x, pad_y = 14, 12
line_h = 24
W = 900
H = pad_y * 2 + line_h * len(LINES)

img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
# Border
d.rectangle([(0, 0), (W - 1, H - 1)], outline="black", width=1)
# Text
y = pad_y
for ln in LINES:
    d.text((pad_x, y), ln, fill="black", font=f_code)
    y += line_h

img.save(OUT)
print(f"Wrote {OUT}  size={img.size}")

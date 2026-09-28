"""Regenerate Q4.4 figure to match the PDF exactly:
    A      B
    |      |
    v      v
    C:\\MYSTUFF\\BUDGET.XLSX

A points to 'MYSTUFF', B points to 'BUDGET.XLSX'. Tight, monospace.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join('static', 'uploads', 'cat_p2_n25', 'q4_4.png')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

W, H = 380, 90
img = Image.new('RGB', (W, H), 'white')
d = ImageDraw.Draw(img)

CONS_B = r'C:\Windows\Fonts\consolab.ttf'
CONS = r'C:\Windows\Fonts\consola.ttf'
ARIB = r'C:\Windows\Fonts\arialbd.ttf'
ARI = r'C:\Windows\Fonts\arial.ttf'

# Path text uses Arial Bold to match the rest of the paper (Arial/Helvetica)
font_path_txt = ImageFont.truetype(ARIB if os.path.exists(ARIB) else ARI, 24)
font_lbl = ImageFont.truetype(ARIB if os.path.exists(ARIB) else ARI, 20)

path_text = r'C:\MYSTUFF\BUDGET.XLSX'
bb = d.textbbox((0, 0), 'H', font=font_path_txt)
char_w = bb[2] - bb[0]

x0 = 20
y_path = 50
d.text((x0, y_path), path_text, fill='black', font=font_path_txt)

# Compute exact x positions of each character using cumulative widths (Arial
# is proportional, not monospace, so we can't just multiply char_w).
char_xs = []
acc = 0
for ch in path_text:
    char_xs.append(x0 + acc)
    acc += d.textlength(ch, font=font_path_txt)
char_xs.append(x0 + acc)  # end position

def span(i, j):
    return char_xs[i], char_xs[j + 1]

A_l, A_r = span(0, 1)   # 'C:' (drive)
B_l, B_r = span(3, 9)   # 'MYSTUFF' (folder)

# Bracket geometry: thin horizontal line above the path with short
# down-ticks at each end (square-bracket opening downward).
y_brk = y_path - 6          # horizontal bracket line
y_tick = y_path - 2         # bottom of vertical down-tick
y_lbl = 6                   # top of letter label

for letter, l, r in [('A', A_l, A_r), ('B', B_l, B_r)]:
    cx = (l + r) / 2
    # horizontal line
    d.line([(l, y_brk), (r, y_brk)], fill='black', width=2)
    # left down-tick
    d.line([(l, y_brk), (l, y_tick)], fill='black', width=2)
    # right down-tick
    d.line([(r, y_brk), (r, y_tick)], fill='black', width=2)
    # label centered above
    bbl = d.textbbox((0, 0), letter, font=font_lbl)
    lw = bbl[2] - bbl[0]
    d.text((cx - lw / 2, y_lbl), letter, fill='black', font=font_lbl)

img.save(OUT, 'PNG')
print(f'Wrote {OUT}  size={img.size}')

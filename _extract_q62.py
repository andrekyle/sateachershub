import fitz, os
os.makedirs('static/uploads/cat_p1_n25', exist_ok=True)
doc = fitz.open(r'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf')
page = doc[16]  # page 17 (0-indexed)
# anchors found:
#   "Your final web page should look like the example below" y1=143.8
#   "Save and close the 6_2Popular" y0=492.6
clip = fitz.Rect(95, 150, 525, 488)
pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip)
out = 'static/uploads/cat_p1_n25/q6_2.png'
pix.save(out)
print('Saved', out, pix.width, 'x', pix.height)

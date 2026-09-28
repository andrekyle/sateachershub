import fitz, os
os.makedirs('static/uploads/cat_p1_n25', exist_ok=True)
doc = fitz.open(r'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf')

# Q7.2 example: page 18 (0-idx 17), between "example below" y=413 and "Step 1" y=574
page = doc[17]
clip = fitz.Rect(150, 420, 545, 568)
pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip)
pix.save('static/uploads/cat_p1_n25/q7_2.png')
print('q7_2.png', pix.width, pix.height)

# Q7.3 time slot table: page 19 (0-idx 18), around y=200-240
page = doc[18]
clip = fitz.Rect(80, 200, 540, 240)
pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip)
pix.save('static/uploads/cat_p1_n25/q7_3.png')
print('q7_3.png', pix.width, pix.height)

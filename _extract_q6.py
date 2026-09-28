"""Extract Q6.1 example webpage figure (page 15-16) and Q6.2 (page 17)."""
import fitz, sqlite3, os
PDF = 'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf'
OUTDIR = 'static/uploads/cat_p1_n25'
os.makedirs(OUTDIR, exist_ok=True)
d = fitz.open(PDF)
c = sqlite3.connect('instance/brandcartel.db')

# Q6.1 stem figure: spans pg 15 (top portion below "Your final web page...")
# through end of pg 15, since 6.1.1 begins on pg 16.
p = d[14]  # page 15
top = max(r.y1 for r in p.search_for("Your final web page should look like the example below")) + 6
bot = p.rect.y1 - 60  # leave footer
clip = fitz.Rect(95, top, p.rect.x1 - 50, bot)
pix = p.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip, alpha=False)
out = os.path.join(OUTDIR, 'q6_1.png')
pix.save(out)
print('Q6.1 saved', out, pix.width, pix.height)
# Attach to Q6.1.1 (first child) so the figure renders right after the
# section opener.
c.execute("UPDATE question_bank_items SET image_path = ? WHERE subtopic = ?",
          ('uploads/cat_p1_n25/q6_1.png', 'CAT P1 Nov 2025 - Q6.1'))

c.commit()
print('done')

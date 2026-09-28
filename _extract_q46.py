"""Extract Q4.6 chart figure from page 11."""
import fitz, sqlite3, os
PDF = 'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf'
OUTDIR = 'static/uploads/cat_p1_n25'
os.makedirs(OUTDIR, exist_ok=True)
d = fitz.open(PDF)
p = d[10]  # page 11
# top: just below the NOTE line
top = max(r.y1 for r in p.search_for("'Term 4'-line series is a smoothed line.")) + 4
# bottom: above "Save and close the 4Students"
bot = min(r.y0 for r in p.search_for("Save and close the 4Students")) - 4
clip = fitz.Rect(90, top, p.rect.x1 - 60, bot)
print('clip', clip)
pix = p.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip, alpha=False)
out = os.path.join(OUTDIR, 'q4_6.png')
pix.save(out)
print('saved', out, pix.width, pix.height)
c = sqlite3.connect('instance/brandcartel.db')
c.execute("UPDATE question_bank_items SET image_path = ? WHERE subtopic = ?",
          ('uploads/cat_p1_n25/q4_6.png', 'CAT P1 Nov 2025 - Q4.6'))
c.commit()
print('db updated')

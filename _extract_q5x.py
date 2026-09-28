"""Extract Q5.2 entry-form figure (page 12) and Q5.3 query result figure
(page 13) and attach to question_bank_items.image_path."""
import fitz, sqlite3, os
PDF = 'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf'
OUTDIR = 'static/uploads/cat_p1_n25'
os.makedirs(OUTDIR, exist_ok=True)
d = fitz.open(PDF)
c = sqlite3.connect('instance/brandcartel.db')

# Q5.2: page 12. Top below "in the example below.", bottom above "Save and close the frm5_2 form."
p = d[11]
top = max(r.y1 for r in p.search_for("in the example below.")) + 4
bot = min(r.y0 for r in p.search_for("Save and close the frm5_2 form")) - 4
clip = fitz.Rect(108, top, p.rect.x1 - 60, bot)
pix = p.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip, alpha=False)
out = os.path.join(OUTDIR, 'q5_2.png')
pix.save(out)
print('Q5.2 saved', out, pix.width, pix.height)
c.execute("UPDATE question_bank_items SET image_path = ? WHERE subtopic = ?",
          ('uploads/cat_p1_n25/q5_2.png', 'CAT P1 Nov 2025 - Q5.2'))

# Q5.3: page 13. Top below "as shown in the example below.", bottom above "Save and close the qry5_3 query."
p = d[12]
rs_top = p.search_for("shown in the example below.")
top = max(r.y1 for r in rs_top) + 4
bot = min(r.y0 for r in p.search_for("Save and close the qry5_3 query")) - 4
clip = fitz.Rect(108, top, p.rect.x1 - 60, bot)
pix = p.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip, alpha=False)
out = os.path.join(OUTDIR, 'q5_3.png')
pix.save(out)
print('Q5.3 saved', out, pix.width, pix.height)
c.execute("UPDATE question_bank_items SET image_path = ? WHERE subtopic = ?",
          ('uploads/cat_p1_n25/q5_3.png', 'CAT P1 Nov 2025 - Q5.3'))

c.commit()
print('done')

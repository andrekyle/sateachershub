"""Find page+anchor for Q4.6 chart."""
import fitz
d = fitz.open('static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf')
for i, p in enumerate(d):
    rs = p.search_for("'Term 4'-line series")
    if rs:
        print('pg', i+1, rs)
    rs2 = p.search_for("Save and close the 4Students")
    if rs2:
        print('  save anchor pg', i+1, rs2)

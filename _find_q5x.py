"""Find pages with Q5.2 / Q5.3 anchors."""
import fitz
d = fitz.open('static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf')
for i, p in enumerate(d):
    for anchor in ["Modify the frm5_2 form",
                   "Save and close the frm5_2 form",
                   "Create a query called qry5_3",
                   "Save and close the qry5_3 query",
                   "Open the qry5_4 query"]:
        rs = p.search_for(anchor)
        if rs:
            print(f'pg {i+1}  {anchor!r}  -> {[(r.x0,r.y0,r.x1,r.y1) for r in rs[:1]]}')

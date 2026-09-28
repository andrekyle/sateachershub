"""Find which words in Q3.1-3.5 are underlined in the source PDF.
Underlines in PDFs appear as thin filled rectangles or as line drawings
just below text baselines; pymupdf can list both via page.get_drawings()."""
import fitz
PDF = r"static/uploads/Computer Applications Technology P2 Nov 2025 Eng.pdf"
doc = fitz.open(PDF)

# find page containing "QUESTION 3" or "non-breaking"
target = None
for pno in range(doc.page_count):
    txt = doc[pno].get_text()
    if 'non-breaking' in txt.lower():
        target = pno
        break
print('page:', target)
page = doc[target]

# find Q3 region: from "QUESTION 3" to "TOTAL SECTION A"
hits_q3 = page.search_for('QUESTION 3')
hits_total = page.search_for('TOTAL SECTION A')
print('QUESTION 3:', hits_q3, 'TOTAL:', hits_total)
y_top = hits_q3[0].y0 if hits_q3 else 0
y_bot = hits_total[0].y0 if hits_total else page.rect.y1
print('y range:', y_top, y_bot)

# get drawings (lines & rects) in the region
drawings = page.get_drawings()
underline_rects = []
for d in drawings:
    for item in d['items']:
        if item[0] == 'l':  # line
            p1, p2 = item[1], item[2]
            if abs(p1.y - p2.y) < 0.5 and y_top <= p1.y <= y_bot and abs(p2.x - p1.x) > 2:
                underline_rects.append(fitz.Rect(min(p1.x, p2.x), p1.y - 0.5, max(p1.x, p2.x), p1.y + 1.5))
        elif item[0] == 're':  # rect
            r = item[1]
            if r.height < 2 and y_top <= r.y0 <= y_bot and r.width > 2:
                underline_rects.append(r)

print(f'found {len(underline_rects)} underline candidates:')
for r in underline_rects:
    # extract text in a tall band ABOVE the underline (not just at it,
    # since the underline sits below baseline)
    band = fitz.Rect(r.x0, r.y0 - 14, r.x1, r.y0 + 1)
    txt = page.get_text(clip=band).strip()
    print(f'  rect={r} text above= {txt!r}')

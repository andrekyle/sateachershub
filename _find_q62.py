import fitz
doc = fitz.open(r'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf')
for pno in range(15, 19):
    page = doc[pno]
    txt = page.get_text()
    if '6.2' in txt and ('6_2Popular' in txt or 'Popular' in txt):
        print(f'=== page {pno+1} ===')
        # find anchors
        for q in ['6.2', '6_2Popular', 'Your final web page should look like the example below', 'Save and close the 6_2Popular', 'ONE mark will be allocated', '[15]']:
            for r in page.search_for(q):
                print(f'  {q!r}: x0={r.x0:.1f} y0={r.y0:.1f} x1={r.x1:.1f} y1={r.y1:.1f}')

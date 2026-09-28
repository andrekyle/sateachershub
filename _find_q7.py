import fitz
doc = fitz.open(r'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf')
print('pages:', doc.page_count)
for pno in range(15, doc.page_count):
    page = doc[pno]
    txt = page.get_text()
    if 'QUESTION 7' in txt or '7Letter' in txt or '7Stats' in txt or 'TotalCost' in txt or 'Time worksheet' in txt:
        print(f'=== page {pno+1} ===')
        for q in ['QUESTION 7','7.1','7.2','7.3','7Letter','7Stats','TotalCost','Time worksheet','Type of course','Step 1','Step 2','Step 3','07:00 07:15','Modify the function in cell D3','Save and close the 7Stats','[15]','[16]','TOTAL:','Work in the TotalCost worksheet','Work in the Time worksheet','example below','head office wants to calculate']:
            for r in page.search_for(q):
                print(f'  {q!r}: x0={r.x0:.1f} y0={r.y0:.1f} x1={r.x1:.1f} y1={r.y1:.1f}')

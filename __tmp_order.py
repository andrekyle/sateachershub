# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import fitz
MG = r"C:\Users\hp\Pictures\southafricanteachershub - new - Copy (3)\static\uploads\Computer Applications Technology P1 Nov 2025 MG Eng.pdf"
doc = fitz.open(MG)

CHROME = ('computer applications technology', 'nsc – marking', 'nsc - marking',
          'copyright reserved', 'please turn over', 'dbe stamp', 'examination',
          'number', 'dbe/november')
def is_chrome(t):
    s = t.strip().lower()
    if not s: return True
    if s.isdigit(): return True
    return any(c in s for c in CHROME)

for pno in (1,8,9,10):
    page = doc[pno]
    tabs = [t for t in page.find_tables().tables if t.col_count >= 4 and t.row_count >= 2]
    tbbox = [t.bbox for t in tabs]
    def in_table(y):
        return any(bb[1]-2 <= y <= bb[3]+2 for bb in tbbox)
    print(f'==== page {pno}: {len(tabs)} tables ====')
    items = []
    for b in page.get_text('blocks'):
        x0,y0,x1,y1,txt = b[0],b[1],b[2],b[3],b[4]
        if in_table(y0): continue
        for ln in txt.split('\n'):
            if ln.strip() and not is_chrome(ln):
                items.append((y0,'T',ln.strip()))
    for t in tabs:
        items.append((t.bbox[1],'TABLE','[%dx%d]'%(t.row_count,t.col_count)))
    for y,k,c in sorted(items):
        print(f'  {y:6.1f} {k:5} {c[:60]}')

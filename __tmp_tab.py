# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import fitz
MG = r"C:\Users\hp\Pictures\southafricanteachershub - new - Copy (3)\static\uploads\Computer Applications Technology P1 Nov 2025 MG Eng.pdf"
doc = fitz.open(MG)
pg = doc[1]
tabs = pg.find_tables()
print('tables found on p1:', len(tabs.tables))
for ti, t in enumerate(tabs.tables):
    print(f'--- table {ti}: rows={t.row_count} cols={t.col_count} bbox={t.bbox} ---')
    data = t.extract()
    for row in data[:12]:
        print([ (c or '').replace(chr(10),' / ')[:40] for c in row ])

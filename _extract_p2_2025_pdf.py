"""Extract the full text of the official CAT P2 May-June 2025 question paper,
page by page, so we can compare Section B against the live generated paper.
"""
import pdfplumber

PDF = r'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'
OUT = r'_p2_2025_pdf.txt'

lines = []
with pdfplumber.open(PDF) as pdf:
    lines.append(f'PAGES: {len(pdf.pages)}')
    for i, page in enumerate(pdf.pages):
        txt = page.extract_text() or ''
        lines.append(f'\n===== PAGE {i+1} =====')
        lines.append(txt)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('wrote', OUT)

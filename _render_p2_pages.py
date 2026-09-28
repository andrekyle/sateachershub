"""Render CAT P2 2025 PDF pages 12 and 13 to high-res PNGs so we can crop
the Q8.4 linked-object figure and the Q8.7 HTML-code + web-page figures.
"""
import pdfplumber

PDF = r'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'

with pdfplumber.open(PDF) as pdf:
    for pno in (12, 13):
        page = pdf.pages[pno - 1]
        im = page.to_image(resolution=200)
        out = f'_p2_page{pno}.png'
        im.save(out)
        print('wrote', out, '| page size', page.width, page.height)

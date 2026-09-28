"""Dump all rects, lines, and images on PDF page 7 to locate the ad box + computer image."""
import pdfplumber

PDF = 'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'

with pdfplumber.open(PDF) as pdf:
    page = pdf.pages[6]
    print('=== RECTS ===')
    for r in page.rects:
        print('x0=%.1f top=%.1f x1=%.1f bottom=%.1f w=%.1f h=%.1f' % (
            r['x0'], r['top'], r['x1'], r['bottom'], r['width'], r['height']))
    print('=== LINES ===')
    for l in page.lines:
        print('x0=%.1f top=%.1f x1=%.1f bottom=%.1f' % (l['x0'], l['top'], l['x1'], l['bottom']))
    print('=== IMAGES ===')
    for im in page.images:
        print('x0=%.1f top=%.1f x1=%.1f bottom=%.1f w=%.1f h=%.1f' % (
            im['x0'], im['top'], im['x1'], im['bottom'], im['width'], im['height']))

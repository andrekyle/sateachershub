"""Locate and crop the StellarX advertisement box from PDF page 7."""
import pdfplumber

PDF = 'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'

with pdfplumber.open(PDF) as pdf:
    page = pdf.pages[6]
    print('page size:', page.width, page.height)
    # Find the "Introducing" word (top of the ad) and "365" / "MS Office 365" (bottom)
    words = page.extract_words()
    top = None
    bot = None
    for w in words:
        if 'Introducing' in w['text']:
            top = w
        if w['text'] == '365':
            bot = w
    print('top:', top)
    print('bot:', bot)
    # Inspect rects to find the bordering rectangle
    rects = page.rects
    print('num rects:', len(rects))
    for r in rects:
        if r['width'] > 300 and r['height'] > 150:
            print('  BIG RECT x0=%.1f top=%.1f x1=%.1f bottom=%.1f w=%.1f h=%.1f' % (
                r['x0'], r['top'], r['x1'], r['bottom'], r['width'], r['height']))

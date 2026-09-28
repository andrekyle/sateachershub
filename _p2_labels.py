import pdfplumber
PDF = r"data/all_uploads/Computer Applications Technology P2 May-June 2024 Eng.pdf"
with pdfplumber.open(PDF) as pdf:
    for pi in (10, 11):
        pg = pdf.pages[pi]
        print(f"=== PAGE {pi} (w={pg.width:.0f} h={pg.height:.0f}) ===")
        for w in pg.extract_words():
            t = w['text']
            if t in ('HTML','CODE:','WEB','PAGE:','Query','1','2','8.2','8.3','8.3.3','Explain','Study'):
                print(f"  {t!r:12} x0={w['x0']:.0f} x1={w['x1']:.0f} top={w['top']:.0f} bottom={w['bottom']:.0f}")
        for im in pg.images:
            print(f"  IMG {im.get('name')} x0={im['x0']:.0f} x1={im['x1']:.0f} top={im['top']:.0f} bottom={im['bottom']:.0f}")

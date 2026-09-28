import pdfplumber
PDF = r"data/all_uploads/Computer Applications Technology P2 May-June 2024 Eng.pdf"
with pdfplumber.open(PDF) as pdf:
    print("NUM PAGES:", len(pdf.pages))
    for i, pg in enumerate(pdf.pages):
        t = pg.extract_text() or ""
        print(f"\n========== PAGE {i} ==========")
        print(t)
        if pg.images:
            print(f"  [IMAGES: {len(pg.images)}]")
            for im in pg.images:
                print("   ", {k: round(v,1) if isinstance(v,(int,float)) else v for k,v in im.items() if k in ('x0','x1','top','bottom','width','height','name')})

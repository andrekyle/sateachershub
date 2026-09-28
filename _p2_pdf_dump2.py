import pdfplumber
PDF = r"data/all_uploads/Computer Applications Technology P2 May-June 2024 Eng.pdf"
out = []
with pdfplumber.open(PDF) as pdf:
    for i in range(6, len(pdf.pages)):
        pg = pdf.pages[i]
        t = pg.extract_text() or ""
        out.append(f"\n========== PAGE {i} ==========")
        out.append(t)
        if pg.images:
            out.append(f"  [IMAGES: {len(pg.images)}]")
            for im in pg.images:
                out.append("   " + str({k: round(v,1) if isinstance(v,(int,float)) else v for k,v in im.items() if k in ('x0','x1','top','bottom','width','height','name')}))
with open("_p2_pdf2.txt","w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("done")

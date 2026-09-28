import pdfplumber, sys
PDF = r"data/all_uploads/Computer Applications Technology P1 May-June 2025 Eng.pdf"
pages = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [5,8,15]
with pdfplumber.open(PDF) as pdf:
    for n in pages:
        pdf.pages[n-1].to_image(resolution=120).save(f"_pdf_p{n}.png")
        print("saved official page", n)

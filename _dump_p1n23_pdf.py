import pdfplumber

PDF = r"static/uploads/Computer Applications Technology P1 Nov 2023 Eng.pdf"
with pdfplumber.open(PDF) as pdf:
    print("NUM PAGES:", len(pdf.pages))
    for i, page in enumerate(pdf.pages):
        txt = page.extract_text() or ""
        print(f"\n========== PAGE {i} (idx) ==========")
        print(txt)

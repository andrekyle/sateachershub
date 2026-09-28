import pdfplumber, io

PDF = r"data/all_uploads/Computer Applications Technology P1 Nov 2023 MG Eng.pdf"
out = io.StringIO()
with pdfplumber.open(PDF) as pdf:
    for i, page in enumerate(pdf.pages):
        out.write(f"\n===== PAGE {i} =====\n")
        out.write(page.extract_text() or "")
        out.write("\n")
open("_memo_pdf_dump.txt", "w", encoding="utf-8").write(out.getvalue())
print("written _memo_pdf_dump.txt")

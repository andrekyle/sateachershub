import fitz, sys, io

PDF = r"data/all_uploads/Computer Applications Technology P1 Nov 2023 MG Eng.pdf"
doc = fitz.open(PDF)
out = io.StringIO()
for i, page in enumerate(doc):
    out.write(f"\n===== PAGE {i} =====\n")
    out.write(page.get_text())
open("_memo_pdf_dump.txt", "w", encoding="utf-8").write(out.getvalue())
print("pages:", len(doc))
print("written _memo_pdf_dump.txt")

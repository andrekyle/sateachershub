import pdfplumber
PDF = r"data\all_uploads\Computer Applications Technology P2 Nov 2022 MG Eng.pdf"
with pdfplumber.open(PDF) as doc:
    for pi in range(min(8, len(doc.pages))):
        txt = doc.pages[pi].extract_text() or ''
        if 'TRUE' in txt.upper() or 'QUESTION 3' in txt.upper() or '3.1' in txt:
            print(f"==== PAGE {pi} ====")
            print(txt.encode('ascii', 'replace').decode('ascii'))
            print()

"""Map PDF pages to questions for CAT P1 May/June 2023."""
import pdfplumber, re

PDF = r'data/all_uploads/Computer Applications Technology P1 May-June 2023 Eng.pdf'
with pdfplumber.open(PDF) as pdf:
    print("TOTAL PAGES:", len(pdf.pages))
    for i, page in enumerate(pdf.pages):
        txt = page.extract_text() or ''
        # find QUESTION markers
        qmarks = re.findall(r'QUESTION\s+(\d+)', txt)
        first = txt.strip().split('\n')[0][:60] if txt.strip() else '(blank)'
        # detect sub-question numbers like 1.1, 2.3, 7.5
        subs = re.findall(r'\b(\d\.\d{1,2}(?:\.\d)?)\b', txt)
        print(f"p{i+1}: QUESTION={qmarks} subs={subs[:8]} | {first}")

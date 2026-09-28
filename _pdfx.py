import pdfplumber, sys
with pdfplumber.open('static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf') as pdf:
    for i,p in enumerate(pdf.pages):
        print(f'--- PAGE {i+1} ---')
        print(p.extract_text() or '')

import pdfplumber
PDF='data/all_uploads/Computer Application Technology P1 May-June 2021 MG Eng.pdf'
with pdfplumber.open(PDF) as pdf:
    for i,pg in enumerate(pdf.pages):
        t=pg.extract_text() or ''
        if '4.3' in t and ('SUMIFS' in t or 'Cell F5' in t):
            print('==== PAGE',i,'====')
            print(t)

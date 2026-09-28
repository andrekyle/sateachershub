import pdfplumber
import sys

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

path = 'data/all_uploads/Computer Applications Technology P1 May-June 2024 Eng.pdf'
try:
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > 3:
            page = pdf.pages[3]
            text = page.extract_text(layout=True)
            if text:
                print(text)
            else:
                print("No text extracted.")
        else:
            print(f"PDF only has {len(pdf.pages)} pages.")
except Exception as e:
    print(f"Error: {e}")

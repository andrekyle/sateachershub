import sys
try:
    import pdfplumber
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'pdfplumber'])
    import pdfplumber

p='data/all_uploads/Computer Applications Technology P1 May-June 2024 Eng.pdf'
with pdfplumber.open(p) as pdf:
    for i,page in enumerate(pdf.pages):
        txt = page.extract_text() or ''
        print(f'\n=========== PAGE {i+1} ===========')
        print(txt)

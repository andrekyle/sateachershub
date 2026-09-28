"""Extract Section B (Q4-Q8) text from the P2 2025 paper + memo PDFs."""
import pdfplumber

PAPER = 'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'
MEMO = 'static/uploads/Computer Applications Technology P2 May-June 2025 MG Eng.pdf'

def dump(path, label):
    print('=' * 80)
    print(label, path)
    print('=' * 80)
    with pdfplumber.open(path) as pdf:
        print('TOTAL PAGES:', len(pdf.pages))
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ''
            print(f'\n----- PAGE {i+1} -----')
            print(txt)

if __name__ == '__main__':
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else 'paper'
    if which == 'paper':
        dump(PAPER, 'PAPER')
    else:
        dump(MEMO, 'MEMO')

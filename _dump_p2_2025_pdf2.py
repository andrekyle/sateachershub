"""Extract Section B text from the P2 2025 paper + memo PDFs to UTF-8 files."""
import pdfplumber

PAPER = 'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'
MEMO = 'static/uploads/Computer Applications Technology P2 May-June 2025 MG Eng.pdf'


def dump(path, out):
    lines = []
    with pdfplumber.open(path) as pdf:
        lines.append(f'TOTAL PAGES: {len(pdf.pages)}')
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ''
            lines.append(f'\n=============== PAGE {i+1} ===============')
            lines.append(txt)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('Wrote', out)


if __name__ == '__main__':
    dump(PAPER, '_p2_paper.txt')
    dump(MEMO, '_p2_memo.txt')

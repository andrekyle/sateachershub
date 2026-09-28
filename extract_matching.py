"""Extract Section A Q2 (matching items) cleanly from each source DBE P2 PDF
using coordinate-aware extraction. COLUMN A and COLUMN B are physically
separated on the page; pdfplumber.extract_words gives us x-coordinates we
can use to split them.

Returns: list of (description_lines[], options[(letter, term)])
"""
import pdfplumber
import re
from collections import defaultdict


_QHEAD_RE = re.compile(r'^(QUESTION\s+\d|SECTION\s+B|TOTAL\s+SECTION)', re.I)


def extract_matching(pdf_path):
    """Find the page containing 'COLUMN A COLUMN B' and split that table."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ''
            if 'COLUMN A' in txt and 'COLUMN B' in txt:
                return _extract_from_page(page)
    return None, None


def _extract_from_page(page):
    # x_tolerance=1 keeps single letters (A, B, ... T) as separate tokens
    # instead of merging them with the following term word.
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False,
                               x_tolerance=1, y_tolerance=2)
    if not words:
        return None, None

    # Locate the COLUMN A header to fix the table top.
    header_top = None
    for i, w in enumerate(words):
        if w['text'] == 'COLUMN' and i + 1 < len(words) and words[i+1]['text'] == 'A':
            header_top = w['top']
            break
    if header_top is None:
        return None, None

    # Body region: below header, above footer / next section.
    body_words = [w for w in words if w['top'] > header_top + 4]
    # Stop at the page footer ("Copyright reserved") or the next QUESTION
    # banner. Important: "copyright" can legitimately appear as a COLUMN B
    # option term, so require it to be followed by "reserved" before
    # treating it as a footer marker.
    sorted_body = sorted(body_words, key=lambda x: x['top'])
    stop_y = None
    for idx, w in enumerate(sorted_body):
        t = w['text']
        nxt = sorted_body[idx + 1]['text'] if idx + 1 < len(sorted_body) else ''
        if t == 'QUESTION':
            stop_y = w['top']; break
        if t.lower().startswith('copyright') and nxt.lower().startswith('reserved'):
            stop_y = w['top']; break
    if stop_y:
        body_words = [w for w in body_words if w['top'] < stop_y - 2]

    # ---- Locate the COLUMN B letter column ---------------------------------
    # The option letters A-T form a vertical stack at a single x-coordinate.
    # Find the x value where the most single-letter tokens appear.
    from collections import Counter
    letter_xs = Counter(
        round(w['x0']) for w in body_words
        if len(w['text']) == 1 and w['text'].isalpha() and w['text'].isupper()
    )
    if not letter_xs:
        return None, None
    letter_col_x, hits = letter_xs.most_common(1)[0]
    if hits < 5:
        return None, None
    # COLUMN B membership: a token belongs to COLUMN B if its x0 is at or
    # beyond the letter-column x (minus a small tolerance for descenders).
    b_x_min = letter_col_x - 2

    left = [w for w in body_words if w['x0'] < b_x_min]
    right = [w for w in body_words if w['x0'] >= b_x_min]

    # ---- Process LEFT column (COLUMN A) ------------------------------------
    desc_lines = _group_lines(left)
    items = []
    cur_label = None
    cur_buf = []
    label_re = re.compile(r'^(\d+\.\d+)$')
    for ln in desc_lines:
        tokens = ln['tokens']
        if tokens and label_re.match(tokens[0]['text']):
            if cur_label:
                items.append((cur_label, ' '.join(cur_buf).strip()))
            cur_label = tokens[0]['text']
            cur_buf = [' '.join(t['text'] for t in tokens[1:])]
        else:
            cur_buf.append(' '.join(t['text'] for t in tokens))
    if cur_label:
        items.append((cur_label, ' '.join(cur_buf).strip()))
    # Trim empty buf entries.
    items = [(lbl, re.sub(r'\s+', ' ', t).strip()) for lbl, t in items if t.strip()]

    # ---- Process RIGHT column (COLUMN B) -----------------------------------
    opt_lines = _group_lines(right)
    options = []
    cur_letter = None
    cur_term = []
    opt_re = re.compile(r'^([A-Z])$')
    trailing_marks_re = re.compile(r'\s*\(\d+\s*x\s*\d+\)\s*\[\d+\]\s*$')
    for ln in opt_lines:
        tokens = ln['tokens']
        if tokens and opt_re.match(tokens[0]['text']):
            if cur_letter:
                term = ' '.join(cur_term).strip()
                options.append((cur_letter, trailing_marks_re.sub('', term).strip()))
            cur_letter = tokens[0]['text']
            cur_term = [' '.join(t['text'] for t in tokens[1:])]
        else:
            cur_term.append(' '.join(t['text'] for t in tokens))
    if cur_letter:
        term = ' '.join(cur_term).strip()
        options.append((cur_letter, trailing_marks_re.sub('', term).strip()))
    options = [(L, re.sub(r'\s+', ' ', t).strip()) for L, t in options]

    return items, options


def _group_lines(words, y_tol=3):
    """Group words into visual lines by their top y-coordinate."""
    if not words:
        return []
    words = sorted(words, key=lambda w: (w['top'], w['x0']))
    lines = []
    cur = {'top': words[0]['top'], 'tokens': [words[0]]}
    for w in words[1:]:
        if abs(w['top'] - cur['top']) <= y_tol:
            cur['tokens'].append(w)
        else:
            cur['tokens'].sort(key=lambda x: x['x0'])
            lines.append(cur)
            cur = {'top': w['top'], 'tokens': [w]}
    cur['tokens'].sort(key=lambda x: x['x0'])
    lines.append(cur)
    return lines


if __name__ == '__main__':
    import sys, glob
    paths = sys.argv[1:] or sorted(glob.glob('data/all_uploads/*P2*Eng*.pdf'))
    for p in paths:
        if 'MG' in p:
            continue
        print('===', p)
        items, options = extract_matching(p)
        if items is None:
            print('  NO MATCHING TABLE FOUND')
            continue
        print(f'  COLUMN A ({len(items)} rows):')
        for lbl, txt in items:
            print(f'    {lbl}  {txt[:80]}')
        print(f'  COLUMN B ({len(options)} options):')
        for L, term in options:
            print(f'    {L}  {term}')

"""Coordinate-aware re-extraction of memo answers from DBE MG PDFs.

The default text-based extractor breaks on Section-A memo pages because
DBE prints MCQ + Matching memos in TWO side-by-side columns; the line
``1.1 B  1   2.1 P  ADSL  1`` collapses to a single string in
``extract_text()`` causing Q1.1's answer to absorb Q2.1's and Q2.x
answers to be empty.

This script:
* Uses ``pdfplumber.extract_words()`` to read coordinates.
* For each page, detects two-column Section-A layout via the presence
  of ``QUESTION 1`` near x≈54 AND ``QUESTION 2`` further right on the
  same baseline. Splits at the midpoint between them.
* For TRUE/FALSE / SECTION B pages and any single-column page, parses
  with the original text-based ``parse_memo``.
* Updates ``QuestionBankItem.answer_text`` (only).

Runs with a 30-worker multiprocessing pool.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import re
from collections import defaultdict
from typing import Dict, List

import pdfplumber

from extract_all_questions import (
    UPLOADS, parse_paper_label, clean_text, parse_memo, extract_marks,
)

_SUB_RE = re.compile(r'^\d+(?:\.\d+){1,3}$')


def _post_clean(v: str) -> str:
    """Strip trailing page-boundary noise and per-line mark badges."""
    if not v:
        return v
    # Cut at first sentinel that marks end of a question's answer block.
    v = re.split(
        r'\n\s*(?:\[\d+\]|TOTAL\s+SECTION|GRAND\s+TOTAL|SECTION\s+[A-Z]\b|QUESTION\s+\d+\b)',
        v, maxsplit=1, flags=re.I,
    )[0]
    # Remove tick characters
    v = re.sub(r'\uf0fc+', '', v)
    # Strip per-line trailing single-digit mark on the LAST line only
    lines = v.splitlines()
    if lines:
        lines[-1] = re.sub(r'\s+\d{1,2}\s*$', '', lines[-1])
    v = '\n'.join(lines)
    # Strip stray footer markers
    v = re.sub(
        r'\s*(?:Please[- ]turn[- ]over|Copyright\s+reserved).*',
        '', v, flags=re.I,
    )
    return v.strip()


def _group_lines(words, ytol=3):
    lines = []
    cur = []
    last_top = None
    for w in sorted(words, key=lambda w: (round(w['top']), w['x0'])):
        if last_top is None or abs(w['top'] - last_top) < ytol:
            cur.append(w)
            if last_top is None:
                last_top = w['top']
        else:
            lines.append(cur)
            cur = [w]
            last_top = w['top']
    if cur:
        lines.append(cur)
    return lines


def _detect_section_a_split(words):
    """Return split_x or None. Detects a 'QUESTION 1' word at x<150 and a
    'QUESTION 2' word at x>200 with both on roughly the same baseline."""
    q1 = q2 = None
    for i, w in enumerate(words):
        if w['text'].upper() != 'QUESTION':
            continue
        if i + 1 >= len(words):
            continue
        nxt = words[i + 1]
        if abs(nxt['top'] - w['top']) > 3:
            continue
        num = nxt['text'].rstrip(':')
        if num == '1' and w['x0'] < 150:
            q1 = w
        elif num == '2' and w['x0'] >= 200:
            q2 = w
    if q1 and q2 and abs(q1['top'] - q2['top']) < 5 and q2['x0'] > q1['x0']:
        # Use slightly left of Q2's header so the mark-badge column for
        # Q1 (typically at x≈245) stays on the LEFT side.
        return q2['x0'] - 10
    return None


def _parse_column_text(text):
    """Standard line-based memo parse for a column of text."""
    out = {}
    current = None
    buf = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            if current and buf:
                buf.append('')
            continue
        m = re.match(r'^(\d+(?:\.\d+){1,3})\s+(.*)$', s)
        if m:
            if current:
                ans = '\n'.join(buf).strip()
                ans, _ = extract_marks(ans)
                out[current] = ans
            current = m.group(1)
            buf = [m.group(2)]
        else:
            if current:
                buf.append(s)
    if current and current not in out:
        ans = '\n'.join(buf).strip()
        ans, _ = extract_marks(ans)
        out[current] = ans
    return out


def _extract_two_col_page(page):
    """Return ({sub_no: answer}, ...) for a two-column Section-A page."""
    words = page.extract_words()
    split_x = _detect_section_a_split(words)
    if split_x is None:
        return None
    lines = _group_lines(words)
    out: Dict[str, str] = {}
    for col_filter in ('left', 'right'):
        current = None
        buf: List[str] = []
        for line in lines:
            if col_filter == 'left':
                col_words = [w for w in line if w['x0'] < split_x]
            else:
                col_words = [w for w in line if w['x0'] >= split_x]
            if not col_words:
                continue
            col_words = sorted(col_words, key=lambda w: w['x0'])
            txt = ' '.join(w['text'] for w in col_words).strip()
            # Drop tick chars early so they don't confuse the sub-no regex
            txt = re.sub(r'\uf0fc+', '', txt).strip()
            # Skip column headers / totals
            if not txt:
                continue
            if re.match(r'^QUESTION\s+\d+', txt, re.I):
                continue
            if re.match(r'^Total:?\s*\[', txt, re.I):
                continue
            # Match sub-no at start of line
            m = re.match(r'^(\d+(?:\.\d+){1,3})\s+(.*)$', txt)
            if m:
                if current:
                    out[current] = (' '.join(buf)).strip()
                current = m.group(1)
                buf = [m.group(2)]
            elif current:
                buf.append(txt)
        if current:
            out[current] = (' '.join(buf)).strip()
    # Strip trailing per-line "1" mark badges
    for k in list(out.keys()):
        v = out[k]
        v = re.sub(r'\uf0fc+', '', v).strip()  # tick characters
        # Strip common page footers if they leaked in
        v = re.sub(
            r'\s*(Please[- ]turn[- ]over|Copyright\s+reserved).*$',
            '', v, flags=re.I).strip()
        v = re.sub(r'\s+\d+\s*$', '', v).strip()  # trailing single-digit mark
        out[k] = v
    return out


def _process_pdf(args):
    path, label = args
    out: Dict[str, str] = {}
    try:
        with pdfplumber.open(path) as pdf:
            full_text_pages = []
            for page in pdf.pages:
                two_col = _extract_two_col_page(page)
                if two_col:
                    for k, v in two_col.items():
                        if v.strip():
                            out[k] = v.strip()
                else:
                    full_text_pages.append(page.extract_text() or '')
            # Single-col pages: use the existing text-based parse_memo on
            # the joined cleaned text (handles Q3 T/F + Section B SAQs)
            cleaned = clean_text('\n'.join(full_text_pages))
            for k, v in parse_memo(cleaned).items():
                if k not in out and v.strip():
                    out[k] = v.strip()
        return {'label': label, 'memo': out, 'err': None}
    except Exception as e:  # noqa: BLE001
        return {'label': label, 'memo': {}, 'err': str(e)}


def main():
    pdfs = []
    for name in os.listdir(UPLOADS):
        path = os.path.join(UPLOADS, name)
        if not os.path.isfile(path) or not name.lower().endswith('.pdf'):
            continue
        info = parse_paper_label(name)
        if not info or not info['is_memo']:
            continue
        pdfs.append((path, info['label']))
    pdfs.sort()
    workers = min(30, len(pdfs) or 1)
    print(f'Parsing {len(pdfs)} memo PDFs with {workers} workers...')
    with mp.Pool(processes=workers) as pool:
        results = pool.map(_process_pdf, pdfs)

    memo_idx: Dict[str, Dict[str, str]] = defaultdict(dict)
    for r in results:
        if r['err']:
            print('ERR', r['label'], r['err'])
            continue
        memo_idx[r['label']].update(r['memo'])
    print(f'Indexed {sum(len(v) for v in memo_idx.values())} memo answers '
          f'across {len(memo_idx)} memos')

    from app import app, db, QuestionBankItem  # noqa: WPS433

    sub_pat = re.compile(r'-\s*Q(\d+(?:\.\d+){0,3})\s*$')
    updates = 0
    blanks_kept = 0
    with app.app_context():
        items = QuestionBankItem.query.filter(
            QuestionBankItem.tags.like('%auto_import_v1%')).all()
        for it in items:
            sub = it.subtopic or ''
            m = sub_pat.search(sub)
            label = sub.split(' - Q')[0].strip() if ' - Q' in sub else ''
            if not m or label not in memo_idx:
                continue
            ans = memo_idx[label].get(m.group(1), '').strip()
            ans = _post_clean(ans)
            if not ans:
                if not (it.answer_text or '').strip():
                    blanks_kept += 1
                continue
            if (it.answer_text or '').strip() != ans:
                it.answer_text = ans
                updates += 1
        db.session.commit()
    print(f'Updated {updates} answers. Still blank: {blanks_kept}')


if __name__ == '__main__':
    main()

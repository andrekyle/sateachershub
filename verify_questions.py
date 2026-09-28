"""Verify every auto-imported QuestionBankItem against its source PDF.

Uses a 20-worker multiprocessing pool. For each paper PDF, extracts the
text, splits into sub-questions (1.1, 1.1.1 ...), and compares the DB
text to the PDF text using normalised fuzzy ratio. Reports mismatches
and missing-from-PDF items to ``verification_report.txt``.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from extract_all_questions import (
    UPLOADS, TAG_MARKER,
    parse_paper_label, extract_pdf_text, clean_text,
    split_into_sections, split_questions_in_section, split_subquestions,
    extract_marks,
)


def _norm(s: str) -> str:
    s = (s or '').lower()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^a-z0-9 ]+', '', s)
    return s.strip()


def parse_pdf_to_subqs(pdf_path: str) -> Tuple[str, Dict[str, str]]:
    """Return (paper_label, {sub_no: normalised_text}). Skips memos."""
    info = parse_paper_label(pdf_path)
    if not info or info['is_memo']:
        return ('', {})
    raw = extract_pdf_text(pdf_path)
    cleaned = clean_text(raw)
    out: Dict[str, str] = {}
    for sec, lines in split_into_sections(cleaned):
        for parent_no, _rest, body in split_questions_in_section(lines):
            for sub_no, text in split_subquestions(parent_no, body):
                text, _ = extract_marks(text)
                out[sub_no] = _norm(text)
    return info['label'], out


def worker(pdf_path: str):
    try:
        label, subs = parse_pdf_to_subqs(pdf_path)
        return {'pdf': pdf_path, 'label': label, 'subs': subs, 'err': None}
    except Exception as e:  # noqa: BLE001
        return {'pdf': pdf_path, 'label': '', 'subs': {}, 'err': str(e)}


def main():
    # Collect non-memo PDFs
    pdfs = []
    for name in os.listdir(UPLOADS):
        path = os.path.join(UPLOADS, name)
        if not os.path.isfile(path) or not name.lower().endswith('.pdf'):
            continue
        info = parse_paper_label(name)
        if not info or info['is_memo']:
            continue
        pdfs.append(path)
    pdfs.sort()
    print(f'Parsing {len(pdfs)} question PDFs with 20 workers...')

    with mp.Pool(processes=min(20, len(pdfs) or 1)) as pool:
        results = pool.map(worker, pdfs)

    # Merge: label -> { sub_no -> normalised PDF text }
    pdf_index: Dict[str, Dict[str, str]] = defaultdict(dict)
    for r in results:
        if r['err']:
            print('PDF ERR', r['pdf'], r['err'])
            continue
        if r['label']:
            pdf_index[r['label']].update(r['subs'])
    print(f'Indexed {sum(len(v) for v in pdf_index.values())} sub-questions across '
          f'{len(pdf_index)} papers')

    # ---- Compare DB items --------------------------------------------
    from app import app, QuestionBankItem  # noqa: WPS433
    sub_pat = re.compile(r'-\s*Q(\d+(?:\.\d+){0,3})\s*$')

    perfect = mismatch = missing = unparsed = 0
    mismatches: List[str] = []
    missing_list: List[str] = []

    with app.app_context():
        items = QuestionBankItem.query.filter(
            QuestionBankItem.tags.like(f'%{TAG_MARKER}%')
        ).all()
        print(f'Verifying {len(items)} bank items...')
        for it in items:
            sub = (it.subtopic or '')
            m = sub_pat.search(sub)
            paper_label = sub.split(' - Q')[0].strip() if ' - Q' in sub else ''
            if not m or paper_label not in pdf_index:
                unparsed += 1
                continue
            sub_no = m.group(1)
            pdf_text = pdf_index[paper_label].get(sub_no)
            db_text = _norm(it.question_text)
            if not pdf_text:
                missing += 1
                missing_list.append(
                    f'[MISSING] {paper_label} Q{sub_no} (id={it.id})')
                continue
            # Fuzzy ratio (db vs pdf) — db should be substring-ish of pdf
            ratio = SequenceMatcher(None, db_text[:600], pdf_text[:600]).ratio()
            # Also try substring containment (pdf-side often has extra
            # context like image refs)
            db_short = db_text[:200]
            contained = db_short in pdf_text if db_short else False
            if ratio >= 0.75 or contained:
                perfect += 1
            else:
                mismatch += 1
                mismatches.append(
                    f'[MISMATCH ratio={ratio:.2f}] {paper_label} Q{sub_no} '
                    f'(id={it.id})\n  DB : {db_text[:200]}\n  PDF: {pdf_text[:200]}\n')

    total = perfect + mismatch + missing + unparsed
    summary = (
        f'\n=== Verification summary ===\n'
        f'Total items checked   : {total}\n'
        f'Exact/near-match (OK) : {perfect}\n'
        f'Mismatched            : {mismatch}\n'
        f'Missing from PDF      : {missing}\n'
        f'Unparseable subtopic  : {unparsed}\n'
        f'Match rate            : {perfect / total * 100:.1f}%\n'
    )
    print(summary)

    with open('verification_report.txt', 'w', encoding='utf-8') as f:
        f.write(summary)
        f.write('\n--- MISMATCHES ---\n')
        f.write('\n'.join(mismatches[:500]))
        f.write(f'\n\n(showing {min(len(mismatches), 500)} of {len(mismatches)})\n')
        f.write('\n--- MISSING ---\n')
        f.write('\n'.join(missing_list[:500]))
        f.write(f'\n\n(showing {min(len(missing_list), 500)} of {len(missing_list)})\n')
    print('Full report -> verification_report.txt')


if __name__ == '__main__':
    main()

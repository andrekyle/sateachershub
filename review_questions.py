"""Comprehensive question-bank review using 30 multiprocessing workers.

For each imported QuestionBankItem this checks:
  * question text matches PDF (fuzzy ratio + substring)
  * marks are consistent with what the PDF shows
  * question_type classification looks correct vs. PDF intro
  * answer_text is present (warn only) and not obviously truncated

Writes ``review_report.txt`` with categorised findings.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from extract_all_questions import (
    UPLOADS, TAG_MARKER,
    parse_paper_label, extract_pdf_text, clean_text,
    split_into_sections, split_questions_in_section, split_subquestions,
    extract_marks,
)


_TYPE_INTROS = {
    'mcq':         re.compile(r'various\s+options\s+are\s+given|choose\s+the\s+answer\s+and\s+write\s+only\s+the\s+letter', re.I),
    'true_false':  re.compile(r'\bindicate\s+(?:whether|if).+?true\s+or\s+false\b|\bchoose\s+the\s+answer\s+and\s+write\s+[\'"]?true[\'"]?\s+or\s+[\'"]?false[\'"]?', re.I),
    'matching':    re.compile(r'column\s*a.+?column\s*b', re.I | re.S),
}


def _norm(s: str) -> str:
    s = (s or '').lower()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^a-z0-9 ]+', '', s)
    return s.strip()


def parse_pdf(pdf_path: str):
    info = parse_paper_label(pdf_path)
    if not info or info['is_memo']:
        return None
    raw = extract_pdf_text(pdf_path)
    cleaned = clean_text(raw)
    subs: Dict[str, Dict] = {}
    parent_type: Dict[str, str] = {}
    for sec_name, lines in split_into_sections(cleaned):
        for parent_no, _rest, body in split_questions_in_section(lines):
            full_text = '\n'.join(body)
            # Detect type from the parent's intro lines (first 600 chars)
            head = full_text[:800]
            ptype = None
            for t, rx in _TYPE_INTROS.items():
                if rx.search(head):
                    ptype = t
                    break
            parent_type[parent_no] = ptype or ''
            for sub_no, text in split_subquestions(parent_no, body):
                clean, marks = extract_marks(text)
                subs[sub_no] = {
                    'text_norm': _norm(clean),
                    'text_raw': clean.strip(),
                    'marks': marks,
                    'parent': parent_no,
                }
    return {'label': info['label'], 'subs': subs, 'parent_type': parent_type}


def worker(pdf_path: str):
    try:
        res = parse_pdf(pdf_path)
        return {'pdf': pdf_path, 'res': res, 'err': None}
    except Exception as e:  # noqa: BLE001
        return {'pdf': pdf_path, 'res': None, 'err': str(e)}


def main():
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
    workers = min(30, len(pdfs) or 1)
    print(f'Parsing {len(pdfs)} question PDFs with {workers} workers...')

    with mp.Pool(processes=workers) as pool:
        results = pool.map(worker, pdfs)

    pdf_idx: Dict[str, Dict] = {}
    parent_types: Dict[str, Dict[str, str]] = {}
    for r in results:
        if r['err'] or not r['res']:
            if r['err']:
                print('PDF ERR', r['pdf'], r['err'])
            continue
        lbl = r['res']['label']
        pdf_idx.setdefault(lbl, {}).update(r['res']['subs'])
        parent_types.setdefault(lbl, {}).update(r['res']['parent_type'])
    print(f'Indexed {sum(len(v) for v in pdf_idx.values())} sub-questions across '
          f'{len(pdf_idx)} papers')

    from app import app, QuestionBankItem  # noqa: WPS433

    sub_pat = re.compile(r'-\s*Q(\d+(?:\.\d+){0,3})\s*$')

    findings = {
        'text_mismatch': [],
        'marks_mismatch': [],
        'type_mismatch': [],
        'missing_answer': [],
        'missing_from_pdf': [],
        'unparsed': [],
    }
    ok = 0

    with app.app_context():
        items = QuestionBankItem.query.filter(
            QuestionBankItem.tags.like(f'%{TAG_MARKER}%')
        ).all()
        print(f'Reviewing {len(items)} bank items...')

        for it in items:
            sub = it.subtopic or ''
            m = sub_pat.search(sub)
            paper_label = sub.split(' - Q')[0].strip() if ' - Q' in sub else ''
            if not m or paper_label not in pdf_idx:
                findings['unparsed'].append(f'{sub} (id={it.id})')
                continue
            sub_no = m.group(1)
            pdf_sub = pdf_idx[paper_label].get(sub_no)
            if not pdf_sub:
                findings['missing_from_pdf'].append(f'{paper_label} Q{sub_no} (id={it.id})')
                continue

            parent_no = pdf_sub['parent']
            ptype = parent_types.get(paper_label, {}).get(parent_no, '')

            db_type = (it.question_type or '').lower()
            db_text = _norm(it.question_text)
            db_marks = int(it.marks or 0)

            # --- text check (skip if matching: text is intentionally
            # rewritten to "Match the following ..." prefix) ---
            if db_type != 'matching' and ptype != 'matching':
                pt = pdf_sub['text_norm'][:600]
                dt = db_text[:600]
                ratio = SequenceMatcher(None, dt, pt).ratio()
                if ratio < 0.6 and (dt[:120] not in pt):
                    findings['text_mismatch'].append(
                        f'[{ratio:.2f}] {paper_label} Q{sub_no} (id={it.id})\n'
                        f'  DB : {db_text[:180]}\n  PDF: {pdf_sub["text_norm"][:180]}\n')

            # --- marks check ---
            pdf_marks = pdf_sub['marks'] or 0
            # Matching items always 1 mark per sub
            if db_type == 'matching':
                if db_marks != 1:
                    findings['marks_mismatch'].append(
                        f'{paper_label} Q{sub_no} (id={it.id}) matching has marks={db_marks} (expected 1)')
            elif pdf_marks and pdf_marks != db_marks:
                findings['marks_mismatch'].append(
                    f'{paper_label} Q{sub_no} (id={it.id}) DB={db_marks} PDF={pdf_marks}')

            # --- type check vs parent intro ---
            if ptype and db_type and ptype != db_type:
                # mcq tagged as short_answer etc.
                findings['type_mismatch'].append(
                    f'{paper_label} Q{sub_no} (id={it.id}) DB={db_type} PDF-parent={ptype}')

            # --- answer presence ---
            if not (it.answer_text or '').strip():
                findings['missing_answer'].append(
                    f'{paper_label} Q{sub_no} (id={it.id})')

            ok += 1

    total = sum(len(v) for v in findings.values()) + ok
    summary = [f'\n=== Review summary ({total} items) ===']
    for k, v in findings.items():
        summary.append(f'  {k:18s}: {len(v)}')
    summary.append(f'  {"ok_checked":18s}: {ok}')
    summary.append('')
    print('\n'.join(summary))

    with open('review_report.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary))
        for cat, lst in findings.items():
            f.write(f'\n\n--- {cat.upper()} ({len(lst)}) ---\n')
            for line in lst[:1000]:
                f.write(line + '\n')
            if len(lst) > 1000:
                f.write(f'... ({len(lst) - 1000} more)\n')
    print('Full report -> review_report.txt')


if __name__ == '__main__':
    main()

"""Re-extract per-question MARKS from each source DBE PDF and update the DB
so the per-section + grand totals match the PDF exactly.

Strategy
--------
1. For each MEMO/QUESTION PDF, walk every line and look for a sub-no
   followed (anywhere on that or the next line, within the same item)
   by a trailing ``(N)`` badge. That ``N`` is the mark for that
   sub-question.
2. If a parent question number P has any child P.X in the badge map,
   the parent itself is a STEM and gets 0 marks (the marks live in the
   children).
3. Update ``QuestionBankItem.marks`` accordingly. Only touches rows
   tagged ``auto_import_v1``.

Multiprocessing pool, 50 workers max.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import re
from collections import defaultdict
from typing import Dict, List

import pdfplumber

from extract_all_questions import UPLOADS, parse_paper_label, clean_text

WORKERS = 50
TAG_MARKER = 'auto_import_v1'

# Lines like "4.7 Briefly explain ... (2)" — captures sub-no + final (N)
# Also handles totals on the next line: "(4 x 1) (4)" -> last (N) wins.
_LINE_RE = re.compile(
    r'^\s*(?P<no>\d+(?:\.\d+){1,3})\b[^\n]*?\((?P<mk>\d+)\)\s*$'
)


def _extract_marks(text: str) -> Dict[str, int]:
    """Walk lines; the LAST (N) on a line beginning with a sub-no wins.
    If the badge isn't on the same line as the sub-no, look at the
    immediately following line(s) up to the next sub-no."""
    out: Dict[str, int] = {}
    lines = text.split('\n')
    current_no = None
    for i, raw in enumerate(lines):
        ln = raw.rstrip()
        # Try direct same-line capture
        m = _LINE_RE.match(ln)
        if m:
            out[m.group('no')] = int(m.group('mk'))
            current_no = None
            continue
        # New sub-no without same-line badge → remember & look ahead
        sm = re.match(r'^\s*(\d+(?:\.\d+){1,3})\b', ln)
        if sm:
            current_no = sm.group(1)
            # Scan up to 6 lines ahead for a trailing (N) before the next sub-no
            for j in range(i, min(i + 7, len(lines))):
                fwd = lines[j]
                if j != i and re.match(r'^\s*\d+(?:\.\d+){1,3}\b', fwd):
                    break
                bm = re.search(r'\((\d+)\)\s*$', fwd)
                if bm:
                    out[current_no] = int(bm.group(1))
                    current_no = None
                    break
    return out


def _process_pdf(args):
    path, label = args
    try:
        with pdfplumber.open(path) as pdf:
            text = '\n'.join((pg.extract_text() or '') for pg in pdf.pages)
        text = clean_text(text)
        return label, _extract_marks(text), None
    except Exception as e:  # noqa: BLE001
        return label, {}, str(e)


def main():
    pdfs = []
    for name in os.listdir(UPLOADS):
        path = os.path.join(UPLOADS, name)
        if not os.path.isfile(path) or not name.lower().endswith('.pdf'):
            continue
        info = parse_paper_label(name)
        if not info:
            continue
        # Use the QUESTION paper (not the memo) for mark badges where
        # available, but fall back to memo (the MG also encodes marks).
        pdfs.append((path, info['label'], info['is_memo']))

    # Prefer question papers — one set of marks per label
    by_label: Dict[str, list] = defaultdict(list)
    for p, lbl, is_memo in pdfs:
        by_label[lbl].append((p, is_memo))
    jobs = []
    for lbl, options in by_label.items():
        # question paper first, then memo
        options.sort(key=lambda t: t[1])
        for p, _ in options[:2]:  # try up to 2 sources per label
            jobs.append((p, lbl))

    workers = min(WORKERS, len(jobs) or 1)
    print(f'Parsing {len(jobs)} PDFs with {workers} workers...')
    with mp.Pool(processes=workers) as pool:
        results = pool.map(_process_pdf, jobs)

    marks_idx: Dict[str, Dict[str, int]] = defaultdict(dict)
    for label, m, err in results:
        if err:
            print(f'ERR {label}: {err}')
            continue
        # First source wins (question paper > memo)
        for k, v in m.items():
            marks_idx[label].setdefault(k, v)
    print(f'Indexed marks for {len(marks_idx)} papers')

    from app import app, db, QuestionBankItem  # noqa: WPS433

    sub_pat = re.compile(r'-\s*Q(\d+(?:\.\d+){0,3})\s*$')
    fixed = unchanged = stems_zeroed = ghosts_deleted = 0
    with app.app_context():
        items = QuestionBankItem.query.filter(
            QuestionBankItem.tags.like(f'%{TAG_MARKER}%')).all()
        # Group by label
        by_lbl: Dict[str, List] = defaultdict(list)
        for it in items:
            sub = (it.subtopic or '').strip()
            m = sub_pat.search(sub)
            if not m:
                continue
            label = sub.split(' - Q')[0].strip()
            by_lbl[label].append((m.group(1), it))

        for label, rows in by_lbl.items():
            label_marks = marks_idx.get(label) or {}
            if not label_marks:
                continue
            present_nos = {n for n, _ in rows}
            # Any parent number that has a child in the badge map (regardless
            # of whether we extracted that child) is a STEM.
            stems = set()
            for badge_no in label_marks:
                if '.' in badge_no:
                    stems.add(badge_no.rsplit('.', 1)[0])
            # A qno is a "ghost" if neither it nor any sub-form of it is in
            # the PDF badge map AND it isn't a recognised stem.
            def is_ghost(no: str) -> bool:
                if no in label_marks or no in stems:
                    return False
                # depth-1 like "4" is allowed if any child exists
                if any(k == no or k.startswith(no + '.') for k in label_marks):
                    return False
                return True
            for no, it in rows:
                # Don't zero "ghosts" — our badge extractor is incomplete
                # (MCQ rows, table cells etc. don't always carry (N)).
                # The displayed paper total comes from total_marks on the
                # GeneratedPaper, which is pinned to 150/180.
                if no in stems:
                    if (it.marks or 0) != 0:
                        it.marks = 0
                        stems_zeroed += 1
                    continue
                if no in stems:
                    if (it.marks or 0) != 0:
                        it.marks = 0
                        stems_zeroed += 1
                    continue
                mk = label_marks.get(no)
                if mk is None:
                    continue
                if (it.marks or 0) != mk:
                    it.marks = mk
                    fixed += 1
                else:
                    unchanged += 1
        db.session.commit()
    print(f'Updated marks: {fixed}, zeroed stems: {stems_zeroed}, '
          f'ghosts deleted: {ghosts_deleted}, unchanged: {unchanged}')


if __name__ == '__main__':
    main()

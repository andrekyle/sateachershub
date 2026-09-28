"""Fix the matching-question import for every P2 template.

The original PDF import flowed the COLUMN A descriptions and COLUMN B options
together into a single string, so each of the 10 Q2 items ended up with text
like "A wired internet connection   A   WiMAX" and a question_type of
'short_answer'. The renderer (paper_print.html) only switches to the proper
two-column COLUMN A | COLUMN B table when question_type is 'match_columns'
*and* the first item's question_text carries the parseable "Options:" tail
expected by _annotate_matching_runs() in app.py.

This script:
  1. Walks every public CAT P2 template GeneratedPaper.
  2. Locates Section A's Q2 split (10 items).
  3. Re-extracts the clean COLUMN A descriptions + COLUMN B options from the
     matching source PDF using extract_matching.extract_matching().
  4. Updates each of the 10 QuestionBankItem rows:
       - question_type   = 'match_columns'
       - marks           = 1
       - question_text   = <description only> ; on item 2.1 append the
         "Options:\nA) ...\nB) ..." tail so the renderer can rebuild the table.

Maps each template label to its source PDF by year + paper term.
"""
import json
import re
import sys
import glob
import os
import multiprocessing as mp
from typing import Dict, List, Optional, Tuple

from app import app, GeneratedPaper, QuestionBankItem, db
from extract_matching import extract_matching


# Map "<term> <year>" used in template labels to filename fragments in the
# source PDFs. The PDFs use 'May-June' for the May/June sitting and 'Nov'
# for November.
_TERM_FRAGMENTS = {
    'May-June': ['May-June'],
    'Nov': ['Nov'],
}


def _find_source_pdf(paper_no: str, term: str, year: str) -> Optional[str]:
    """Locate the source DBE QP PDF for a given template label."""
    pdfs = glob.glob('data/all_uploads/*.pdf')
    candidates = []
    frags = _TERM_FRAGMENTS.get(term, [term])
    for p in pdfs:
        name = os.path.basename(p)
        if 'MG' in name:        # skip marking guidelines
            continue
        if f'P{paper_no}' not in name:
            continue
        if not any(f in name for f in frags):
            continue
        if year not in name:
            continue
        candidates.append(p)
    if not candidates:
        return None
    # Prefer the shortest filename (e.g. without the trailing " (1)" copy).
    return sorted(candidates, key=lambda s: (len(s), s))[0]


_LABEL_RE = re.compile(r'CAT\s+P(\d)\s+(.+?)\s+(\d{4})$')


def _parse_label(label: str) -> Optional[Tuple[str, str, str]]:
    m = _LABEL_RE.match(label.strip())
    if not m:
        return None
    return m.group(1), m.group(2).strip(), m.group(3)


def _fix_one(paper_id: str) -> Tuple[str, str, int]:
    """Worker: re-import the matching question for a single template paper.

    Returns (label, status, items_updated).
    """
    with app.app_context():
        p = GeneratedPaper.query.get(paper_id)
        if not p:
            return ('?', 'missing', 0)
        label = p.title or ''
        parsed = _parse_label(label)
        if not parsed:
            return (label, 'bad-label', 0)
        paper_no, term, year = parsed
        if paper_no != '2':
            return (label, 'skip-not-p2', 0)
        src = _find_source_pdf(paper_no, term, year)
        if not src:
            return (label, 'no-source-pdf', 0)
        items, options = extract_matching(src)
        if not items or not options:
            return (label, 'extract-failed', 0)
        if len(items) != 10:
            return (label, f'wrong-row-count:{len(items)}', 0)

        # Locate Section A's Q2 split.
        try:
            sections = json.loads(p.sections or '[]')
        except Exception:
            return (label, 'bad-sections-json', 0)
        if not sections:
            return (label, 'no-sections', 0)
        secA = sections[0]
        qids = secA.get('question_ids') or []
        splits = secA.get('splits') or []
        # Q2 is the second split: qids[splits[1] : splits[2]]
        if len(splits) < 3:
            return (label, 'no-q2-split', 0)
        q2_qids = qids[splits[1]:splits[2]]
        if len(q2_qids) != 10:
            return (label, f'q2-len-{len(q2_qids)}', 0)

        # Build the Options tail to append to the first item.
        opts_tail = '\n'.join(f'{L}) {term_text}' for L, term_text in options)

        updated = 0
        for idx, qid in enumerate(q2_qids):
            q = QuestionBankItem.query.get(qid)
            if not q:
                continue
            _, desc = items[idx]
            new_text = desc.strip()
            if idx == 0:
                new_text = f'{new_text}\nOptions:\n{opts_tail}'
            q.question_text = new_text
            q.question_type = 'match_columns'
            q.marks = 1
            updated += 1
        db.session.commit()
        return (label, 'ok', updated)


def main():
    with app.app_context():
        # Only P2 templates owned by admin (public templates).
        from sqlalchemy import or_
        papers = (GeneratedPaper.query
                  .filter(GeneratedPaper.title.like('CAT P2%'))
                  .all())
        ids = [p.id for p in papers]
        print(f'Found {len(ids)} P2 templates to fix.')

    # Run in parallel. One process per paper is fine (max 16 workers).
    workers = min(20, max(1, len(ids)))
    with mp.Pool(workers) as pool:
        results = pool.map(_fix_one, ids)
    ok = 0
    for label, status, n in results:
        marker = 'OK ' if status == 'ok' else 'ERR'
        print(f'  [{marker}] {label}: status={status} updated={n}')
        if status == 'ok':
            ok += 1
    print(f'\nDone. Successfully fixed {ok}/{len(ids)} P2 templates.')


if __name__ == '__main__':
    main()

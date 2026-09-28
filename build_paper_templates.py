"""Build / refresh one public GeneratedPaper "template" per DBE source PDF.

A teacher visiting /teacher/generator sees these because they are
``share_scope='public'``. They can click *Clone* to drop a full editable
copy of the paper into their own workspace and use it as a starting
point.

Each template is built so that on load it already renders 1:1 with the
DBE PDF:

* Sections A / B / C — discovered from the ``section_<L>`` tag on each
  auto-imported question.
* Top-level Questions (Q1, Q2, Q3, Q4, …) — discovered from the parent
  question number embedded in the ``subtopic`` field (e.g.
  ``CAT P2 May-June 2025 - Q4.3.1`` → parent = 4). These become the
  ``splits`` array in the section JSON.
* Sub-items — depth-3 (e.g. 4.1.1) numbers go into the ``subitems``
  array so the editor / printer renders them with hanging indent.
* Per-Question titles + DBE intros for Section A (MULTIPLE-CHOICE,
  MATCHING ITEMS, TRUE/FALSE) are pre-filled.
* Section-level instructions remain blank (intros live on each Question
  for Section A; B/C use the question stems themselves).
* Cover instructions are pre-filled from the same library used by the
  editor's "Auto-detect instructions" button.

Multiprocessing pool size capped at 50.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from app import (
    app, db, GeneratedPaper, QuestionBankItem, User, INSTRUCTION_LIBRARY,
)

WORKERS = 50
TAG_MARKER = 'auto_import_v1'

_SUB_RE = re.compile(r'^(.+?)\s*-\s*Q(\d+(?:\.\d+){0,3})\s*$')
_SECTION_TAG_RE = re.compile(r'(?:^|,)\s*section_([A-Z])\s*(?:,|$)')


def _section_letter(tags: str, qno: str) -> str:
    m = _SECTION_TAG_RE.search(tags or '')
    if m:
        return m.group(1).upper()
    head = int(qno.split('.')[0])
    return 'A' if head <= 3 else 'B'


def _sort_key(qno: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in qno.split('.'))


# Maps a question_type to the Section-A category (used for qtitles / qinstr).
_A_CAT_BY_TYPE = {
    'mcq':                 'Section A — Multiple-choice',
    'multiple_choice':     'Section A — Multiple-choice',
    'match_columns':       'Section A — Matching items',
    'matching':            'Section A — Matching items',
    'true_false':          'Section A — True/False items',
    'truefalse':           'Section A — True/False items',
    'true_false_correct':  'Section A — True/False items',
}
_A_TITLE = {
    'Section A — Multiple-choice':  'MULTIPLE-CHOICE QUESTIONS',
    'Section A — Matching items':   'MATCHING ITEMS',
    'Section A — True/False items': 'TRUE/FALSE ITEMS',
}


def _qinstr_for(cat: str) -> str:
    lines = INSTRUCTION_LIBRARY.get(cat) or []
    if not lines:
        return ''
    return '[Auto] ' + cat + '\n' + '\n'.join(lines)


def _build_for_label(args):
    """Worker: return (label, sections_payload, cover_categories)."""
    label, rows = args
    # rows: list of (qno, qid, qtype, tags, marks, topic)
    is_p1 = ' P1 ' in f' {label} '

    by_section: Dict[str, List] = defaultdict(list)
    for qno, qid, qtype, tags, _marks, _topic in rows:
        sec = _section_letter(tags, qno)
        by_section[sec].append((_sort_key(qno), qid, qno, (qtype or '').lower()))

    sections_payload = []
    for letter in sorted(by_section.keys()):
        rows_s = sorted(by_section[letter], key=lambda t: t[0])
        question_ids = [qid for _, qid, _qno, _ in rows_s]
        # splits: indices where parent_no changes
        splits: List[int] = []
        last_parent = None
        for i, (key, _qid, _qno, _qt) in enumerate(rows_s):
            parent = key[0]
            if parent != last_parent:
                splits.append(i)
                last_parent = parent
        # subitems: indices that are depth-3 within their group
        subitems: List[int] = []
        split_set = set(splits)
        for i, (key, _qid, _qno, _qt) in enumerate(rows_s):
            if i in split_set:
                continue
            if len(key) >= 3:  # e.g. 4.1.1 -> depth 3
                subitems.append(i)

        # Per-Question titles + intros (only Section A gets DBE auto intros)
        qtitles: List[str] = []
        qinstructions: List[str] = []
        for split_idx in splits:
            qt = rows_s[split_idx][3]
            cat = _A_CAT_BY_TYPE.get(qt) if letter == 'A' else None
            if cat:
                qtitles.append(_A_TITLE[cat])
                qinstructions.append(_qinstr_for(cat))
            else:
                qtitles.append('')
                qinstructions.append('')

        sec = {
            'title': f'Section {letter}',
            'instructions': '',
            'question_ids': question_ids,
            'splits': splits,
            'qtitles': qtitles,
            'qinstructions': qinstructions,
            'subitems': subitems,
        }
        sections_payload.append(sec)

    # Cover-level categories. The DBE cover INSTRUCTIONS AND INFORMATION page
    # is a single flat 1-N list drawn entirely from the Paper-type library
    # (12 items for P2, 20 for P1). Subject-specific notes (Web/Databases)
    # and general conduct items are NOT part of the DBE cover -- they belong
    # under their respective questions / are embedded in the Paper-type list.
    cover_cats = []
    if is_p1:
        cover_cats.append('Paper 1 — Practical (cover instructions)')
    else:
        cover_cats.append('Paper 2 — Theory (cover instructions)')

    return label, sections_payload, cover_cats


def _build_cover_instructions(cats: List[str]) -> str:
    """Build the cover-page instruction text.

    Each individual instruction line from the library becomes its own
    numbered <li> in paper_print.html, because items are separated by a
    blank line ('\\n\\n'). Within a single library entry, embedded '\\n'
    line-breaks survive as continuation paragraphs / bullets under the
    same numbered item (used for "This question paper consists of:" and
    the P1 "Do the following:" bullet sub-list).

    A leading '[Auto] <Category>' marker is included on the first item so
    the editor's auto-detect/auto-fill flow can identify and replace
    previously-generated blocks. The marker is suppressed at print time
    by paper_print.html.
    """
    items: List[str] = []
    for ci, c in enumerate(cats):
        lines = INSTRUCTION_LIBRARY.get(c) or []
        for li, line in enumerate(lines):
            if ci == 0 and li == 0:
                items.append('[Auto] ' + c + '\n' + line)
            else:
                items.append(line)
    return '\n\n'.join(items)


def _parse_label(label: str):
    m = re.match(r'CAT\s+P(\d)\s+(.+?)\s+(\d{4})$', label)
    if not m:
        return {'paper_number': '', 'term': '', 'year': ''}
    return {'paper_number': m.group(1), 'term': m.group(2), 'year': m.group(3)}


def main():
    with app.app_context():
        items = (QuestionBankItem.query
                 .filter(QuestionBankItem.tags.like(f'%{TAG_MARKER}%'))
                 .all())
        admin = (User.query.filter_by(is_admin=True).first()
                 or User.query.first())
        if not admin:
            print('No users in DB; aborting.')
            return
        owner_id = admin.id

        buckets: Dict[str, List] = defaultdict(list)
        for it in items:
            m = _SUB_RE.match(it.subtopic or '')
            if not m:
                continue
            label, qno = m.group(1).strip(), m.group(2)
            buckets[label].append((
                qno, it.id, it.question_type or '', it.tags or '',
                it.marks or 0, it.topic or '',
            ))

        if not buckets:
            print('No labelled items found.')
            return

        jobs = sorted(buckets.items())
        workers = min(WORKERS, len(jobs))
        print(f'Building {len(jobs)} paper templates with {workers} workers...')
        with mp.Pool(processes=workers) as pool:
            built = pool.map(_build_for_label, jobs)

        created = updated = 0
        for label, sections_payload, cover_cats in built:
            meta = _parse_label(label)
            existing = (GeneratedPaper.query
                        .filter_by(owner_id=owner_id, title=label)
                        .first())
            sections_json = json.dumps(sections_payload)
            cover_text = _build_cover_instructions(cover_cats)
            paper_no = meta['paper_number'] or ('1' if 'P1' in label else '2')
            # DBE CAT: P1 practical = 180 marks; P2 theory = 150 marks.
            paper_total = 180 if paper_no == '1' else 150

            common = dict(
                subject='Computer Applications Technology',
                grade=12,
                duration_minutes=180,
                total_marks=paper_total,
                paper_number=paper_no,
                cover_subtitle='Past Paper Template',
                instructions=cover_text,
                sections=sections_json,
                share_scope='public',
                moderation_status='signed_off',
            )
            if existing:
                for k, v in common.items():
                    setattr(existing, k, v)
                existing.title = label
                updated += 1
            else:
                gp = GeneratedPaper(owner_id=owner_id, title=label, **common)
                db.session.add(gp)
                created += 1
        db.session.commit()
        n_qs = sum(len(s['question_ids']) for _, secs, _ in built for s in secs)
        print(f'Templates created={created}, updated={updated}, '
              f'total questions linked={n_qs}.')


if __name__ == '__main__':
    main()

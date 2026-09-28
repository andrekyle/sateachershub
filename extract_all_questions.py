"""Extract every question (and matching memo answer) from every past-paper
PDF in static/uploads/ and insert them into the QuestionBankItem table.

Workflow
--------
1. Walk ``static/uploads`` and pair each question PDF with its memo
   (MG) PDF by filename.
2. Use a multiprocessing pool with 20 workers to parse the PDFs in
   parallel. Each worker returns a list of structured questions and
   memo blocks for its file.
3. In the main process, pair memo blocks with question blocks by paper
   and question number, classify each question's type from its text,
   and bulk-insert ``QuestionBankItem`` rows.

The script is idempotent for the paper-tag set it just imported: it
deletes any prior items tagged ``auto_import_v1`` before re-inserting.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

UPLOADS = os.path.join('static', 'uploads')
TAG_MARKER = 'auto_import_v1'


# ---------------------------------------------------------------------------
# Paper-name parsing
# ---------------------------------------------------------------------------

_PAPER_RE = re.compile(
    r'(?ix)'
    r'computer\s+applications?\s+technology'
    r'\s+P(?P<paper>\d)'
    r'\s+(?P<term>May[-\s/]?June|Nov(?:ember)?|June|February|March|September)'
    r'\s+(?P<year>20\d{2})'
)


def parse_paper_label(filename: str) -> Optional[dict]:
    """Return {paper, term, year, label, is_memo} or None."""
    base = os.path.basename(filename)
    stem = os.path.splitext(base)[0]
    m = _PAPER_RE.search(stem)
    if not m:
        return None
    paper = m.group('paper')
    term = m.group('term').replace(' ', '').replace('/', '-')
    if term.lower().startswith('nov'):
        term_short = 'Nov'
    elif term.lower().startswith('may'):
        term_short = 'May-June'
    else:
        term_short = term.capitalize()
    year = m.group('year')
    is_memo = bool(re.search(r'\bMG\b', stem, re.I))
    label = f'CAT P{paper} {term_short} {year}'
    return {
        'paper': paper,
        'term': term_short,
        'year': year,
        'label': label,
        'is_memo': is_memo,
        'filename': base,
    }


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: str) -> str:
    """Best-effort text extraction. pdfplumber first, then pypdf."""
    try:
        import pdfplumber  # type: ignore
        out = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    out.append(page.extract_text(layout=True,
                                                 x_density=7.25,
                                                 y_density=13) or '')
                except Exception:
                    try:
                        out.append(page.extract_text() or '')
                    except Exception:
                        out.append('')
        return '\n'.join(out)
    except Exception:
        pass
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:
            return ''
    try:
        reader = PdfReader(pdf_path)
        return '\n'.join((p.extract_text() or '') for p in reader.pages)
    except Exception:
        return ''


def clean_text(raw: str) -> str:
    """Strip DBE headers/footers, page numbers, and PUA control chars."""
    lines = []
    for ln in raw.splitlines():
        body = ln.rstrip()
        s = body.strip()
        if not s:
            lines.append('')
            continue
        if re.fullmatch(r'\d{1,3}', s):
            continue
        if re.search(r'(?i)copyright reserved', s):
            continue
        if re.search(r'(?i)please turn over', s):
            continue
        if re.search(r'(?i)\bDBE/(?:[A-Za-z]+/?)*\s*\d{4}\b', s):
            continue
        if re.search(r'(?i)/P\d+\s+\d{1,3}\s+DBE/', s):
            continue
        if re.search(r'(?i)^NSC|SC/NSC', s):
            continue
        body = (body.replace('\uf0b7', '\u2022')
                    .replace('\uf0a7', '\u2022')
                    .replace('\uf076', '\u2022')
                    .replace('\uf0a8', '\u2022'))
        body = re.sub(
            r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ue000-\uf8ff\ufffd]',
            '', body)
        body = re.sub(r'<[^>]{1,80}>', '', body)
        lines.append(body)
    # Collapse multiple blank lines
    out = []
    blank = 0
    for ln in lines:
        if ln == '':
            blank += 1
            if blank <= 1:
                out.append('')
        else:
            blank = 0
            out.append(ln)
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# Sub-question splitting (1.1, 1.2, 2.1.1 ...)
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r'^\s*SECTION\s+([A-Z])\b\s*(.*)$', re.I)
_QUESTION_RE = re.compile(r'^\s*QUESTION\s+(\d+)\b\s*(.*)$', re.I)
# Sub-question numbers: "1.1", "1.1.1", "2.4.3" etc. at line start.
_SUB_RE = re.compile(r'^\s*(\d+(?:\.\d+){1,3})\s+(.+)$')
# Trailing "(N)" or "[N]" indicates marks.
_TRAIL_MARKS = re.compile(r'(?:\((\d{1,3})\)|\[(\d{1,3})\])\s*$')


@dataclass
class Question:
    paper_label: str
    paper_no: str
    year: str
    term: str
    section: str           # 'A', 'B', etc.
    question_no: str       # '1.1', '1.1.1' or '1' (top-level only)
    parent_no: str         # '1', '2' ...
    text: str
    marks: int = 0
    qtype: str = 'short_answer'
    answer: str = ''


def split_into_sections(cleaned: str) -> List[Tuple[str, List[str]]]:
    """Return [(section_letter, [lines...]), ...] ; default 'A' if none."""
    sections: List[Tuple[str, List[str]]] = []
    current_letter = 'A'
    current_lines: List[str] = []
    seen = False
    for ln in cleaned.splitlines():
        m = _SECTION_RE.match(ln)
        if m:
            if seen:
                sections.append((current_letter, current_lines))
            current_letter = m.group(1).upper()
            current_lines = []
            seen = True
            continue
        current_lines.append(ln)
    sections.append((current_letter, current_lines))
    if not seen:
        # Single fall-through section
        return sections
    # Drop any leading 'A' bucket from before the first SECTION marker if empty
    return [s for s in sections if any(l.strip() for l in s[1])]


def split_questions_in_section(lines: List[str]) -> List[Tuple[str, str, List[str]]]:
    """Within a section, split into top-level QUESTION blocks.

    Returns [(parent_no, header_rest, body_lines), ...]
    """
    blocks: List[Tuple[str, str, List[str]]] = []
    current_no: Optional[str] = None
    current_rest = ''
    current_body: List[str] = []
    for ln in lines:
        m = _QUESTION_RE.match(ln)
        if m:
            if current_no is not None:
                blocks.append((current_no, current_rest, current_body))
            current_no = m.group(1)
            current_rest = (m.group(2) or '').strip()
            current_body = []
            continue
        if current_no is not None:
            current_body.append(ln)
    if current_no is not None:
        blocks.append((current_no, current_rest, current_body))
    return blocks


def split_subquestions(parent_no: str, body: List[str]) -> List[Tuple[str, str]]:
    """Split a question body into sub-questions by leading numeric tag.

    Returns [(subnumber, text), ...]. If no sub-numbers are found, returns
    a single tuple (parent_no, joined_text).
    """
    items: List[Tuple[str, List[str]]] = []
    current_no: Optional[str] = None
    current_lines: List[str] = []
    for ln in body:
        m = _SUB_RE.match(ln)
        if m and m.group(1).startswith(parent_no + '.'):
            if current_no is not None:
                items.append((current_no, current_lines))
            current_no = m.group(1)
            current_lines = [m.group(2)]
        else:
            if current_no is None:
                # pre-amble belongs to "parent" intro; keep accumulating
                if current_lines or ln.strip():
                    current_lines.append(ln)
            else:
                current_lines.append(ln)
    if current_no is not None:
        items.append((current_no, current_lines))
        # Promote pre-amble (if any) to the parent number as context
        # Already attached above to first sub if we want; skip for now.
    elif current_lines:
        items.append((parent_no, current_lines))

    out: List[Tuple[str, str]] = []
    for num, ln_list in items:
        text = '\n'.join(ln_list).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        if text:
            out.append((num, text))
    return out


def extract_marks(text: str) -> Tuple[str, int]:
    """Return (text_with_marks_trimmed, marks_int)."""
    marks = 0
    m = _TRAIL_MARKS.search(text.rstrip())
    if m:
        marks = int(m.group(1) or m.group(2) or 0)
        text = _TRAIL_MARKS.sub('', text.rstrip()).rstrip()
    return text, marks


# ---------------------------------------------------------------------------
# Question-type classification
# ---------------------------------------------------------------------------

def classify(text: str) -> str:
    t = text.lower()
    head = text[:400].lower()
    if re.search(r'column\s+a.*column\s+b', t, re.S) or 'column a' in head:
        return 'matching'
    # MCQ: A.  ...  B.  ...  C.  ...  D.  ...  or  A) ...
    if re.search(r'(^|\n)\s*A[\.\)]\s+.+\n\s*B[\.\)]\s+', text):
        return 'mcq'
    if re.search(r'\bchoose\b.*\b(correct answer|from the list)', t):
        return 'mcq'
    if re.search(r'\b(true or false|true/false)\b', t):
        return 'true_false'
    if re.search(r'\bgive (one|two|three|the) word', t):
        return 'one_word'
    if 'fill in the' in t and 'blank' in t:
        return 'fill_in_blank'
    if re.search(r'\b(define|definition of|give the term)\b', t):
        return 'definition'
    if re.search(r'\b(list|name|identify|state|mention)\b\s+(one|two|three|four|five|\d+)', t):
        return 'list'
    if re.search(r'\b(advantage[s]?\s+and\s+disadvantage[s]?|two\s+advantages|two\s+disadvantages)\b', t):
        return 'advantages_disadvantages'
    if re.search(r'\bcompare\b|\bdifference\s+between\b|\bdistinguish\b', t):
        return 'compare'
    if re.search(r'\bdiscuss\b|\bmotivate\b', t):
        return 'discuss'
    if re.search(r'\bexplain\b|\bdescribe\b|\bbriefly\b', t):
        return 'explain'
    if re.search(r'\bcalculate\b|\bworkings?\b', t):
        return 'calculation'
    if re.search(r'\bin a paragraph\b|\bessay\b', t):
        return 'paragraph'
    if re.search(r'\b(html|<\s*\w+\s*>)\b', t):
        return 'html_web'
    if re.search(r'\b(excel|spreadsheet|formula|=sum|=if|=vlookup)\b', t):
        return 'spreadsheet'
    if re.search(r'\b(word\s+processing|microsoft word|ms word)\b', t):
        return 'word_processing'
    if re.search(r'\b(access|database|query|table design)\b', t):
        return 'database'
    return 'short_answer'


# ---------------------------------------------------------------------------
# Memo parsing — match sub-numbers to answer text
# ---------------------------------------------------------------------------

def parse_memo(cleaned: str) -> dict:
    """Return mapping {sub_number: answer_text}.

    DBE memos use the same 1.1, 1.1.1 ... numbering convention.
    """
    out: dict = {}
    current_no: Optional[str] = None
    current_lines: List[str] = []
    for ln in cleaned.splitlines():
        m = _SUB_RE.match(ln)
        if m:
            if current_no is not None:
                out[current_no] = '\n'.join(current_lines).strip()
            current_no = m.group(1)
            current_lines = [m.group(2)]
        else:
            if current_no is not None:
                current_lines.append(ln)
    if current_no is not None and current_no not in out:
        out[current_no] = '\n'.join(current_lines).strip()
    # Trim trailing "(N)" marks markers from memo answers
    for k, v in list(out.items()):
        v, _ = extract_marks(v)
        # Cap absurdly large memos (some include scenario text)
        out[k] = v[:4000]
    return out


# ---------------------------------------------------------------------------
# Per-PDF worker
# ---------------------------------------------------------------------------

def worker(pdf_path: str) -> dict:
    """Parse one PDF and return either questions or memo answers.

    Returned dict shape:
      {
        'paper_label': str,
        'is_memo': bool,
        'paper_no': str, 'year': str, 'term': str,
        'questions': [Question.__dict__, ...]     # if not memo
        'memo': {sub_no: answer_text}            # if memo
      }
    """
    meta = parse_paper_label(pdf_path) or {}
    if not meta:
        return {'error': f'unrecognised: {pdf_path}'}
    raw = extract_pdf_text(pdf_path)
    cleaned = clean_text(raw)
    base = {
        'paper_label': meta['label'],
        'paper_no': meta['paper'],
        'year': meta['year'],
        'term': meta['term'],
        'is_memo': meta['is_memo'],
        'filename': meta['filename'],
    }
    if meta['is_memo']:
        base['memo'] = parse_memo(cleaned)
        base['questions'] = []
        return base
    out_questions: List[dict] = []
    for letter, lines in split_into_sections(cleaned):
        for parent_no, header_rest, body in split_questions_in_section(lines):
            full_body = [header_rest] + body if header_rest else body
            subs = split_subquestions(parent_no, full_body)
            for sub_no, sub_text in subs:
                txt, marks = extract_marks(sub_text)
                qtype = classify(txt)
                out_questions.append({
                    'paper_label': meta['label'],
                    'paper_no': meta['paper'],
                    'year': meta['year'],
                    'term': meta['term'],
                    'section': letter,
                    'question_no': sub_no,
                    'parent_no': parent_no,
                    'text': txt[:6000],
                    'marks': marks,
                    'qtype': qtype,
                })
    base['questions'] = out_questions
    base['memo'] = {}
    return base


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pdfs: List[str] = []
    for name in os.listdir(UPLOADS):
        path = os.path.join(UPLOADS, name)
        if not os.path.isfile(path):
            continue
        if not name.lower().endswith('.pdf'):
            continue
        if parse_paper_label(name) is None:
            continue
        pdfs.append(path)
    pdfs.sort()
    print(f'Found {len(pdfs)} past-paper PDFs')

    # ---- Parse in parallel with 20 workers ---------------------------
    with mp.Pool(processes=min(20, len(pdfs) or 1)) as pool:
        results = pool.map(worker, pdfs)

    # ---- Pair memo answers with questions by paper_label -------------
    memo_by_paper: dict = {}
    q_results: List[dict] = []
    for r in results:
        if not r or r.get('error'):
            if r and r.get('error'):
                print('SKIP', r['error'])
            continue
        if r['is_memo']:
            memo_by_paper.setdefault(r['paper_label'], {}).update(r['memo'])
        else:
            q_results.append(r)

    # ---- Bulk insert -------------------------------------------------
    from app import app, db, QuestionBankItem, User  # noqa: WPS433

    with app.app_context():
        admin = (User.query.filter_by(is_admin=True).first()
                 or User.query.first())
        if not admin:
            sys.exit('No user available to own imported questions.')
        owner_id = admin.id
        print(f'Owner: {admin.email} ({owner_id})')
        # Idempotent: drop any prior auto-imported items
        existing = QuestionBankItem.query.filter(
            QuestionBankItem.tags.like(f'%{TAG_MARKER}%')).count()
        if existing:
            QuestionBankItem.query.filter(
                QuestionBankItem.tags.like(f'%{TAG_MARKER}%')).delete(
                synchronize_session=False)
            db.session.commit()
            print(f'Removed {existing} prior auto-imported items')

        inserted = 0
        seen_texts = set()
        for r in q_results:
            memo = memo_by_paper.get(r['paper_label'], {})
            for q in r['questions']:
                # Skip duplicate question text (some papers repeat MCQs)
                norm_key = re.sub(r'\s+', ' ', (q['text'] or '').lower()).strip()[:500]
                if norm_key and norm_key in seen_texts:
                    continue
                seen_texts.add(norm_key)
                # MCQs in DBE papers are always 1 mark each
                if q['qtype'] == 'mcq' and (q['marks'] or 0) > 3:
                    q['marks'] = 1
                answer = memo.get(q['question_no'], '')
                tags = [
                    TAG_MARKER,
                    'imported',
                    'past_paper',
                    r['paper_label'],
                    f"P{r['paper_no']}",
                    r['year'],
                    r['term'],
                    f"section_{q['section']}",
                    f"Q{q['parent_no']}",
                    q['qtype'],
                ]
                topic = (
                    'Theory' if r['paper_no'] == '2' else 'Practical'
                )
                item = QuestionBankItem(
                    owner_id=owner_id,
                    grade=12,
                    subject='Computer Applications Technology',
                    topic=topic,
                    subtopic=f"{r['paper_label']} - Q{q['question_no']}",
                    difficulty='medium',
                    question_type=q['qtype'],
                    question_text=q['text'],
                    answer_text=answer,
                    marks=q['marks'] or 1,
                    tags=','.join(tags),
                    share_scope='public',
                )
                db.session.add(item)
                inserted += 1
                if inserted % 200 == 0:
                    db.session.commit()
                    print(f'  ...committed {inserted}')
        db.session.commit()
        print(f'Inserted {inserted} QuestionBankItem rows')

        # Summary
        from collections import Counter
        counter = Counter()
        for r in q_results:
            for q in r['questions']:
                counter[(r['paper_label'], q['qtype'])] += 1
        print('\nPer-paper breakdown:')
        last_label = None
        for (label, qtype), n in sorted(counter.items()):
            if label != last_label:
                print(f'\n  {label}')
                last_label = label
            print(f'    {qtype:25s} {n:4d}')


if __name__ == '__main__':
    mp.freeze_support()
    main()

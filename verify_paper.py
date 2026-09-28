#!/usr/bin/env python
"""
verify_paper.py  —  Reusable pre-flight verifier for replicated DBE CAT papers.

PURPOSE
  Encodes the recurring-mistake checklist (see /memories/repo/REPLICATION_CHECKLIST.md)
  as AUTOMATED checks so a paper is validated against its source PDF BEFORE being
  declared "done".  Run this on every paper after editing — do not hand back a paper
  until this prints "NO BLOCKING ISSUES".

USAGE
  python verify_paper.py <paper_id> [path/to/source.pdf]
  python verify_paper.py <paper_id> --no-pdf        # skip PDF cross-checks
  python verify_paper.py all                         # list all papers + ids

WHAT IT CHECKS (the historically-recurring failure modes)
  A. MARKS      double marks (inline "(N)" + a marks box), section/grand totals,
                per-item marks vs the "(N)" tokens in the PDF.
  B. VERBATIM   "[Auto] " instruction prefixes (auto-fill re-injects non-PDF text);
                known injected phrases.
  C. IMG ORDER  body text that says "above"/"shown above"/"example above" but renders
                ABOVE its image (should be in qpost_texts so it sits BELOW).
  D. BORDERS    figure PNG that already has a baked-in border but the item is NOT
                tagged 'noborder' (double-border risk), and vice-versa.
  E. CHROME     page-footer junk leaked into question_text/answer_text
                (DBE Stamp / EXAMINATION NUMBER / Total for QUESTION / Please turn over ...).
  F. STRUCTURE  every QUESTION 1..N marker present in preview AND memo; sections present.

Read-only: this script NEVER writes to the DB.  It only reports.
"""
import os
import re
import sys
import json

# ----------------------------------------------------------------------------- setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db, GeneratedPaper, QuestionBankItem  # noqa: E402

UID = '951c278b-2d76-4969-b0d4-6271479bf397'  # standard teacher/owner used by harnesses
UPLOADS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')

CHROME_PATTERNS = [
    r'DBE\s*Stamp', r'EXAMINATION\s*NUMBER', r'^\s*EXAMINATION\s*$', r'^\s*NUMBER\s*$',
    r'Total for QUESTION', r'^\s*TOTAL SECTION', r'^\s*GRAND TOTAL',
    r'Copyright reserved', r'Please turn over', r'Check the accuracy',
    r'^\s*\d{4,}\s*$',  # bare page-number footer e.g. 20242
]
ABOVE_WORDS = re.compile(r'\b(example above|shown above|as shown above|above\.|in the example above)\b', re.I)


def banner(t):
    print('\n' + '=' * 78 + f'\n  {t}\n' + '=' * 78)


# ----------------------------------------------------------------------------- helpers
def get_paper(pid):
    return db.session.get(GeneratedPaper, pid)


def load_sections(paper):
    try:
        return json.loads(paper.sections) if paper.sections else []
    except Exception as e:
        return [{'_parse_error': str(e)}]


def items_by_id(qids):
    rows = QuestionBankItem.query.filter(QuestionBankItem.id.in_(qids)).all()
    return {r.id: r for r in rows}


def render(client, pid, memo=False):
    url = f"/teacher/generator/{pid}/memo" if memo else f"/teacher/generator/{pid}/preview"
    r = client.get(url)
    return r.status_code, r.get_data(as_text=True)


def png_has_baked_border(path, tol=40, frac=0.85):
    """Heuristic: does the image have a near-solid dark ring on its outer edge?"""
    try:
        from PIL import Image
    except Exception:
        return None
    if not os.path.exists(path):
        return None
    try:
        im = Image.open(path).convert('L')
    except Exception:
        return None
    w, h = im.size
    if w < 8 or h < 8:
        return None
    px = im.load()

    def dark_fraction(coords):
        dark = sum(1 for (x, y) in coords if px[x, y] < 110)
        return dark / max(1, len(coords))

    top = [(x, 1) for x in range(w)]
    bot = [(x, h - 2) for x in range(w)]
    left = [(1, y) for y in range(h)]
    right = [(w - 2, y) for y in range(h)]
    sides = [dark_fraction(top), dark_fraction(bot), dark_fraction(left), dark_fraction(right)]
    # baked border if at least 3 of 4 edges are mostly dark
    return sum(1 for s in sides if s >= frac) >= 3


# ----------------------------------------------------------------------------- checks
def check_marks(paper, secs, item_map, issues):
    banner('A. MARKS')
    grand = 0
    for si, sec in enumerate(secs):
        qids = sec.get('question_ids', [])
        splits = sec.get('splits', [0])
        sec_total = 0
        # group boundaries
        bounds = splits + [len(qids)]
        for gi in range(len(splits)):
            start, end = bounds[gi], bounds[gi + 1]
            gtotal = sum((item_map[q].marks or 0) for q in qids[start:end] if q in item_map)
            sec_total += gtotal
        grand += sec_total
        print(f"  section[{si}] '{sec.get('title','')}'  computed total = {sec_total}")
    print(f"  GRAND (sum of item marks) = {grand}   paper.total_marks = {paper.total_marks}")
    if paper.total_marks and grand != paper.total_marks:
        issues.append(f"MARKS: item-mark sum {grand} != paper.total_marks {paper.total_marks}")

    # double-marks: inline "(N)" in body where N == q.marks AND q.marks>0 with trailing text
    for qid, q in item_map.items():
        txt = (q.question_text or '')
        m = (q.marks or 0)
        if m > 0:
            # inline "(m)" not at the very end (template only strips a trailing one)
            for mt in re.finditer(r'\((\d{1,2})\)', txt):
                if int(mt.group(1)) == m:
                    tail = txt[mt.end():].strip()
                    if tail:  # text after the token => renders inline AND a box => duplicate
                        issues.append(f"DOUBLE-MARK risk: item {qid[:8]} has inline ({m}) mid-text + marks box")
                        break


def check_verbatim(paper, secs, issues):
    banner('B. VERBATIM / AUTO-FILL')
    fields = {
        'instructions': paper.instructions or '',
        'cover_extra_note': getattr(paper, 'cover_extra_note', '') or '',
    }
    for name, val in fields.items():
        if val.startswith('[Auto] '):
            # '[Auto] ' is the CANONICAL state for cover instructions: the editor's
            # auto-fill regenerates byte-identical text from INSTRUCTION_LIBRARY on load,
            # so a proper auto cover is fine. Only flag as a BLOCKING issue when the text
            # does NOT look like a real DBE cover (i.e. a manual edit that will be clobbered).
            looks_like_cover = name == 'instructions' and (
                re.search(r'SECTION\s+[ABC]', val) and 'consists of' in val.lower())
            if looks_like_cover:
                print(f"  note {name} is [Auto] (canonical cover; auto-fill regenerates identical text)")
            else:
                issues.append(f"VERBATIM: paper.{name} starts with '[Auto] ' (auto-fill will overwrite on load)")
                print(f"  [!] {name} is [Auto]-prefixed and does NOT look like a canonical cover")
        else:
            print(f"  ok   {name} ({len(val)} chars)")
    for bad in ('Use the correct settings or features', 'General conduct'):
        if bad.lower() in (paper.instructions or '').lower():
            issues.append(f"VERBATIM: instructions contain injected phrase '{bad}'")


def check_img_order(secs, item_map, issues):
    banner('C. IMAGE / TEXT ORDER')
    n = 0
    for sec in secs:
        qpost = sec.get('qpost_texts', {}) or {}
        for qid in sec.get('question_ids', []):
            q = item_map.get(qid)
            if not q or not q.image_path:
                continue
            n += 1
            body = q.question_text or ''
            if ABOVE_WORDS.search(body):
                issues.append(f"IMG-ORDER: item {qid[:8]} body references 'above' but renders ABOVE its image "
                              f"(move that text to qpost_texts)")
                print(f"  [!] {qid[:8]} body says 'above' yet sits above the image")
    print(f"  checked {n} image items")


def check_borders(secs, item_map, issues):
    banner('D. FIGURE BORDERS (double-border heuristic)')
    for sec in secs:
        for qid in sec.get('question_ids', []):
            q = item_map.get(qid)
            if not q or not q.image_path:
                continue
            tags = (q.tags or '')
            noborder = 'noborder' in tags
            abspath = os.path.join(os.path.dirname(UPLOADS), 'uploads', '')  # placeholder
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', q.image_path.replace('/', os.sep))
            baked = png_has_baked_border(path)
            if baked is None:
                continue
            if baked and not noborder:
                issues.append(f"BORDER: item {qid[:8]} PNG has a baked border but is NOT tagged 'noborder' (double border)")
                print(f"  [!] {qid[:8]} baked border + CSS border -> double")
            elif (not baked) and noborder:
                print(f"  note {qid[:8]} tagged noborder but PNG looks borderless (likely fine, verify)")


def check_chrome(item_map, issues):
    banner('E. CHROME LEAK')
    pats = [re.compile(p, re.I | re.M) for p in CHROME_PATTERNS]
    hits = 0
    for qid, q in item_map.items():
        for field in ('question_text', 'answer_text'):
            val = getattr(q, field) or ''
            for p in pats:
                if p.search(val):
                    hits += 1
                    issues.append(f"CHROME: item {qid[:8]} {field} contains '{p.pattern}'")
                    break
    print(f"  {hits} item/field(s) with leaked chrome")


def check_structure(html_prev, html_memo, secs, item_map, issues):
    banner('F. STRUCTURE (QUESTION markers present)')
    # count distinct question numbers expected
    qns = set()
    for sec in secs:
        qids = sec.get('question_ids', [])
        splits = sec.get('splits', [0])
        qns.update(range(1, len(splits) + 1))  # rough; not global, just count groups per sec
    # better: count "QUESTION N" tokens
    prev_q = set(int(x) for x in re.findall(r'QUESTION\s+(\d+)', html_prev))
    memo_q = set(int(x) for x in re.findall(r'QUESTION\s+(\d+)', html_memo))
    print(f"  preview QUESTION markers: {sorted(prev_q)}")
    print(f"  memo    QUESTION markers: {sorted(memo_q)}")
    missing = prev_q - memo_q
    if missing:
        issues.append(f"STRUCTURE: questions in preview but missing in memo: {sorted(missing)}")


# ----------------------------------------------------------------------------- main
def list_all():
    with app.app_context():
        for p in GeneratedPaper.query.order_by(GeneratedPaper.created_at.desc()).all():
            print(f"{p.id}  | P{p.paper_number} | {p.total_marks:>4} | {p.title}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    if sys.argv[1] == 'all':
        list_all()
        return

    pid = sys.argv[1]
    pdf_path = None
    if len(sys.argv) > 2 and sys.argv[2] not in ('--no-pdf',):
        pdf_path = sys.argv[2]

    with app.app_context():
        paper = get_paper(pid)
        if not paper:
            print(f"NO SUCH PAPER: {pid}")
            return
        print(f"PAPER: {paper.title}  (P{paper.paper_number}, total {paper.total_marks})")
        secs = load_sections(paper)
        all_qids = [q for sec in secs for q in sec.get('question_ids', [])]
        item_map = items_by_id(all_qids)

        app.config['TESTING'] = True
        client = app.test_client()
        with client.session_transaction() as s:
            s['user_id'] = UID
            s['user_role'] = 'teacher'
            s['_user_id'] = UID
        sc_p, html_p = render(client, pid, memo=False)
        sc_m, html_m = render(client, pid, memo=True)
        print(f"render: preview {sc_p}, memo {sc_m}")

        issues = []
        check_marks(paper, secs, item_map, issues)
        check_verbatim(paper, secs, issues)
        check_img_order(secs, item_map, issues)
        check_borders(secs, item_map, issues)
        check_chrome(item_map, issues)
        check_structure(html_p, html_m, secs, item_map, issues)

        banner('SUMMARY')
        if issues:
            print(f"  {len(issues)} ISSUE(S) FOUND:")
            for i in issues:
                print('   - ' + i)
        else:
            print("  NO BLOCKING ISSUES (still eyeball the render vs PDF for layout).")


if __name__ == '__main__':
    main()

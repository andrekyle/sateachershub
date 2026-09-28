"""Strip duplicated footer tails (mark indicators, section totals, grand totals)
from the last QuestionBankItem of each section in every CAT P2 / P1 paper."""
from app import app, GeneratedPaper, QuestionBankItem, db
import json, re

FOOTER_PATTERNS = [
    re.compile(r'\s*GRAND\s*TOTAL\s*:\s*\d+\s*$', re.I),
    re.compile(r'\s*TOTAL\s+SECTION\s+[A-Z]\s*:\s*\d+\s*$', re.I),
    re.compile(r'\s*\[\s*\d+\s*\]\s*$'),
]
TRAILING_MARK_RE = re.compile(r'\s*\(\s*\d+\s*\)\s*$')

def strip_footer(text: str) -> str:
    t = text.rstrip()
    changed = True
    had_footer = False
    while changed:
        changed = False
        for pat in FOOTER_PATTERNS:
            new = pat.sub('', t)
            if new != t:
                t = new.rstrip()
                changed = True
                had_footer = True
    if had_footer:
        # strip trailing duplicate mark indicator like "(1)"
        new = TRAILING_MARK_RE.sub('', t)
        if new != t:
            t = new.rstrip()
    return t

def main():
    app.app_context().push()
    total = 0
    papers = GeneratedPaper.query.filter(GeneratedPaper.title.like('CAT P%')).all()
    for p in papers:
        secs = json.loads(p.sections) if isinstance(p.sections, str) else (p.sections or [])
        ids = []
        for s in secs:
            ids.extend(s.get('question_ids') or s.get('qids') or [])
        items = QuestionBankItem.query.filter(QuestionBankItem.id.in_(ids)).all()
        for q in items:
            t = q.question_text or ''
            if 'TOTAL SECTION' not in t and 'GRAND TOTAL' not in t and not re.search(r'\[\s*\d+\s*\]\s*$', t.rstrip()):
                continue
            new = strip_footer(t)
            if new != t:
                q.question_text = new
                total += 1
                print(f'  - {p.title} {q.id}: stripped')
    db.session.commit()
    print(f'updated {total} items')

if __name__ == '__main__':
    main()

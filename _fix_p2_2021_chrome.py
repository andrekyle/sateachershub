import json, re
from app import app, db, GeneratedPaper, QuestionBankItem

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'

CHROME = re.compile(
    r'^\s*(\(\d+\)|\[\d+\]|TOTAL\s+SECTION\s+[ABC]\s*:?\s*\d+|GRAND\s+TOTAL\s*:?\s*\d+)\s*$',
    re.I)


def strip_trailing_chrome(text):
    lines = text.rstrip('\n').split('\n')
    while lines and (CHROME.match(lines[-1]) or not lines[-1].strip()):
        lines.pop()
    return '\n'.join(lines).rstrip()


with app.app_context():
    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    for si in (1, 2):
        last = secs[si]['question_ids'][-1]
        q = db.session.get(QuestionBankItem, last)
        before = q.question_text
        after = strip_trailing_chrome(before)
        q.question_text = after
        print(f'Section {si} last item {q.id[:8]}:')
        print('  now ends:', repr(after[-80:]))
    db.session.commit()

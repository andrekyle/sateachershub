"""Fix Section B marks, trailing mark/total tokens, and the Q4.7/4.8 memo bleed
for CAT P2 May-June 2025. Paper-affecting fixes (marks + question_text) plus a
memo data-integrity fix.
"""
import re
import app
from app import QuestionBankItem, db

# qid -> correct item mark (last sub-q of each Q was imported as the Q total)
MARK_FIXES = {
    'f9d649a3-6025-45f1-9f47-b7e0f65affe1': 2,  # 4.10.2 (was 25)
    'c2e75d07-1306-435b-b5f5-5d97b45b886e': 2,  # 5.7    (was 15)
    'cea45abe-5850-4ae8-99a2-4af4c5c725eb': 2,  # 6.5.2  (was 10)
    '9248f9d3-e140-4d5d-b19d-a05fcc71caf8': 2,  # 7.6    (was 10)
}

# Trailing "(N)" / "[15]" / "TOTAL SECTION B" garbage to strip from question_text.
TRAILING_RE = re.compile(r'\s*\(\d{1,3}\)\s*(?:\[\d+\]\s*)?(?:TOTAL\s+SECTION\s+B[:\s]*\d*\s*)?$',
                         re.IGNORECASE | re.DOTALL)

TEXT_CLEAN_QIDS = [
    'f9d649a3-6025-45f1-9f47-b7e0f65affe1',  # 4.10.2
    'c2e75d07-1306-435b-b5f5-5d97b45b886e',  # 5.7
    'cea45abe-5850-4ae8-99a2-4af4c5c725eb',  # 6.5.2
    '9248f9d3-e140-4d5d-b19d-a05fcc71caf8',  # 7.6
    '6884ccc9-8fda-4d27-9972-ef7d2dee008a',  # 8.7.3 (has (1)[15]TOTAL SECTION B: 75)
]

Q47_QID = '138ae7ab-dcf2-4833-8af5-84b4a49dd314'  # 4.7 (answer has 4.8 bleed)
Q48_QID = 'dabea055-564a-4c04-b58e-1c37d8267665'  # 4.8 (answer empty)


def main():
    with app.app.app_context():
        for qid, m in MARK_FIXES.items():
            q = QuestionBankItem.query.get(qid)
            print(f'marks {qid[:8]}: {q.marks} -> {m}')
            q.marks = m

        for qid in TEXT_CLEAN_QIDS:
            q = QuestionBankItem.query.get(qid)
            old = q.question_text or ''
            new = TRAILING_RE.sub('', old).rstrip()
            if new != old:
                print(f'text  {qid[:8]}: ...{old[-40:]!r} -> ...{new[-40:]!r}')
                q.question_text = new

        # Memo bleed: 4.7 answer ends with 4.8 content; split it out.
        q47 = QuestionBankItem.query.get(Q47_QID)
        a47 = q47.answer_text or ''
        # Cut at the "4.8" marker that leaked in.
        m = re.search(r'\n\s*4\.8\.?\s*Explain multitasking', a47)
        if m:
            head = a47[:m.start()].rstrip()
            # Drop any stray trailing " 2" mark digit on the (Any two) line.
            head = re.sub(r'\(Any two\)\s*\d?\s*$', '(Any two)', head)
            q47.answer_text = head
            q48 = QuestionBankItem.query.get(Q48_QID)
            if not (q48.answer_text or '').strip():
                q48.answer_text = ('Explain multitasking\n'
                                   'Multitasking allows the operating system to run multiple '
                                   'programs simultaneously')
            print(f'memo  4.7 trimmed; 4.8 answer set ({len(q48.answer_text)} chars)')

        db.session.commit()
        print('committed')


if __name__ == '__main__':
    main()

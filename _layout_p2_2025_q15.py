"""Lay out CAT P2 May-June 2025 Q1.5 as stem -> HTML-table figure -> options.

The options were inside question_text, which renders BEFORE the figure, so
the table appeared below the options. We move the stem to question_text and
push the A-D options into the section's qpost_texts map (rendered after the
figure), with the (1) mark trailing the last option.
"""
import json

import app
from app import GeneratedPaper, QuestionBankItem, db

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'
QID = '7369fb99-76bc-4edb-8782-b9f3bb81d477'

STEM = 'Identify the attribute that was used in the last row of the HTML table below.'
OPTIONS = 'A  Rowspan\nB  Cell spacing\nC  Colspan\nD  Cell padding (1)'


def main():
    with app.app.app_context():
        q = QuestionBankItem.query.get(QID)
        if not q:
            raise SystemExit('Question not found: ' + QID)
        print('OLD question_text:\n', repr(q.question_text))
        q.question_text = STEM

        p = GeneratedPaper.query.get(PAPER_ID)
        secs = json.loads(p.sections)
        s = secs[0]
        qpost = s.get('qpost_texts') or {}
        if not isinstance(qpost, dict):
            qpost = {}
        qpost[QID] = OPTIONS
        s['qpost_texts'] = qpost
        secs[0] = s
        p.sections = json.dumps(secs, ensure_ascii=False)

        db.session.commit()
        print('NEW question_text:\n', repr(q.question_text))
        print('qpost_texts[QID]:\n', repr(qpost[QID]))
        print('image_path:', q.image_path, '| width:', q.image_width, '| offset:', q.image_offset)


if __name__ == '__main__':
    main()

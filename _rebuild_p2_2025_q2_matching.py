"""Rebuild CAT P2 May-June 2025 Question 2 (Matching Items) cleanly.

The PDF extraction garbled Q2 — Column A descriptions were interleaved with
Column B option fragments. We rebuild each of the 10 items with a clean
Column A description, mark them as match_columns (marks=1), embed the full
Column B option list (A-T) on the first item's "Options:" tail, and set the
section title + intro so the template's match-table renderer produces the
official DBE layout.

Memo answers (answer_text) are left untouched — they already hold the correct
letter+term for each row.
"""
import json

import app
from app import GeneratedPaper, QuestionBankItem, db

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

DESCRIPTIONS = [
    'A wired internet connection',
    'A device that connects computers in a network to the internet',
    'Splits the pages in a word processing document to be formatted differently',
    'A device that has the ability to access areas that are too difficult or dangerous for humans to reach',
    'An authentication used to distinguish between humans and bots',
    'An operator that returns a TRUE result when either one of the two criteria is true',
    'Software that updates and fixes multiple errors in applications',
    'When large amounts of data are challenging for a person to process',
    'A method that captures every character a user inputs without their consent',
    'Verification of information with other sources',
]

OPTIONS = [
    ('A', 'WiMAX'),
    ('B', 'information overload'),
    ('C', 'section break'),
    ('D', 'drone'),
    ('E', 'phishing'),
    ('F', 'CAPTCHA'),
    ('G', 'patch'),
    ('H', 'router'),
    ('I', 'page break'),
    ('J', 'big data'),
    ('K', 'accuracy'),
    ('L', 'VR helmet'),
    ('M', 'OR'),
    ('N', 'OTP'),
    ('O', 'AND'),
    ('P', 'ADSL'),
    ('Q', 'service pack'),
    ('R', 'keylogging'),
    ('S', 'NIC'),
    ('T', 'currency'),
]

INTRO = ('Choose a term/concept from COLUMN B that matches the description in '
         'COLUMN A. Write only the letter (A\u2013T) next to the question numbers '
         '(2.1 to 2.10) in the ANSWER BOOK, e.g. 2.11 U.')


def main():
    with app.app.app_context():
        p = GeneratedPaper.query.get(PAPER_ID)
        secs = json.loads(p.sections)
        s = secs[0]
        qids = s['question_ids']
        splits = s['splits']
        start, end = splits[1], splits[2]  # Q2 = indices [10, 20)
        q2_ids = qids[start:end]
        assert len(q2_ids) == 10, f'expected 10 Q2 items, got {len(q2_ids)}'

        opts_block = 'Options:\n' + '\n'.join(f'{ltr}) {term}' for ltr, term in OPTIONS)

        items = {q.id: q for q in QuestionBankItem.query.filter(QuestionBankItem.id.in_(q2_ids)).all()}
        for idx, qid in enumerate(q2_ids):
            q = items[qid]
            desc = DESCRIPTIONS[idx]
            if idx == 0:
                q.question_text = desc + '\n\n' + opts_block
            else:
                q.question_text = desc
            q.question_type = 'match_columns'
            q.marks = 1
            # Clear any stray figure that extraction may have attached.
            q.image_path = q.image_path or ''
            print(f'2.{idx+1}: {desc[:55]!r}  ans={q.answer_text!r}')

        # Section title + intro for Question 2.
        qtitles = s.get('qtitles') or ['', '', '']
        while len(qtitles) < 3:
            qtitles.append('')
        qtitles[1] = 'MATCHING ITEMS'
        s['qtitles'] = qtitles

        qinstr = s.get('qinstructions') or ['', '', '']
        while len(qinstr) < 3:
            qinstr.append('')
        qinstr[1] = INTRO
        s['qinstructions'] = qinstr

        secs[0] = s
        p.sections = json.dumps(secs, ensure_ascii=False)
        db.session.commit()
        print('\nSaved. qtitles=', qtitles)


if __name__ == '__main__':
    main()
